"""Seismic stations and waveforms via FDSN (ObsPy), plus theoretical arrival times."""
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from obspy import Stream, UTCDateTime
from obspy.geodetics import gps2dist_azimuth, kilometers2degrees

from app.config import (
    FDSN_PROVIDER, HTTP_TIMEOUT, MAX_STATIONS, POST_P_SECONDS, STATION_RADIUS_DEG,
)
from app.errors import InsufficientDataError, InvalidRequestError, NotFoundError, UpstreamError

BAND_PREFERENCE = ["HH", "BH"]


@dataclass(frozen=True)
class ChannelInfo:
    network: str
    station: str
    location: str
    channel: str
    lat: float
    lon: float


@dataclass
class StationInfo:
    network: str
    station: str
    location: str
    band: str
    lat: float
    lon: float
    distance_km: float

    @property
    def id(self) -> str:
        return f"{self.network}.{self.station}.{self.location}.{self.band}"


def select_stations(channels: list[ChannelInfo], lat: float, lon: float) -> list[StationInfo]:
    """Keep stations with Z plus N/E (or 1/2) in a preferred band; one per station."""
    components: dict[tuple, set[str]] = defaultdict(set)
    coords: dict[tuple, tuple[float, float]] = {}
    for c in channels:
        band = c.channel[:2]
        if band in BAND_PREFERENCE:
            key = (c.network, c.station, c.location, band)
            components[key].add(c.channel[2])
            coords[key] = (c.lat, c.lon)

    best: dict[tuple, tuple] = {}
    for key, comps in components.items():
        if "Z" not in comps or not ({"N", "E"} <= comps or {"1", "2"} <= comps):
            continue
        net, sta, loc, band = key
        rank = (BAND_PREFERENCE.index(band), loc)
        if (net, sta) not in best or rank < best[(net, sta)][0]:
            best[(net, sta)] = (rank, key)

    result = []
    for _, key in best.values():
        slat, slon = coords[key]
        dist_m, _, _ = gps2dist_azimuth(lat, lon, slat, slon)
        result.append(StationInfo(*key, lat=slat, lon=slon, distance_km=round(dist_m / 1000, 1)))
    result.sort(key=lambda s: s.distance_km)
    return result[:MAX_STATIONS]


def parse_station_id(station_id: str) -> tuple[str, str, str, str]:
    parts = station_id.split(".")
    if len(parts) != 4 or not parts[0] or not parts[1] or not parts[3]:
        raise InvalidRequestError(f"Station id must look like NET.STA.LOC.BAND, got '{station_id}'")
    return parts[0], parts[1], parts[2], parts[3]


def stream_to_array(stream: Stream) -> tuple[np.ndarray, float, UTCDateTime]:
    """Merge gaps, keep Z/N/E, trim to the common span. Returns ((3, N), fs, start)."""
    st = stream.copy()
    st.merge(method=1, fill_value=0)
    by_comp = {}
    for tr in st:
        comp = tr.stats.channel[-1]
        if comp in "ZNE" and comp not in by_comp:
            by_comp[comp] = tr
    if set(by_comp) != {"Z", "N", "E"}:
        raise InsufficientDataError("Station is missing one of the Z/N/E channels")
    rates = {tr.stats.sampling_rate for tr in by_comp.values()}
    if len(rates) != 1:
        raise InsufficientDataError("Channels have different sampling rates")
    start = max(tr.stats.starttime for tr in by_comp.values())
    end = min(tr.stats.endtime for tr in by_comp.values())
    if end <= start:
        raise InsufficientDataError("Channels do not overlap in time")
    traces = [by_comp[c].copy().trim(start, end) for c in "ZNE"]
    n = min(len(t.data) for t in traces)
    data = np.stack([t.data[:n].astype(np.float32) for t in traces])
    return data, rates.pop(), start


def orient_to_zne(stream: Stream, inventory) -> Stream:
    """Rotate Z/1/2 to Z/N/E using the channel azimuths/dips in the inventory."""
    if {tr.stats.channel[-1] for tr in stream} >= {"Z", "N", "E"}:
        return stream
    st = stream.copy()
    try:
        st.rotate("->ZNE", inventory=inventory)
    except Exception as e:
        raise InsufficientDataError("Could not orient the horizontal channels") from e
    return st


@lru_cache(maxsize=1)
def _taup():
    from obspy.taup import TauPyModel

    return TauPyModel(model="iasp91")


def theoretical_arrivals(distance_km: float, depth_km: float) -> tuple[float | None, float | None]:
    """First P and first S travel times (s after origin) from the iasp91 model."""
    arrivals = _taup().get_travel_times(
        source_depth_in_km=max(depth_km, 0.0),
        distance_in_degree=kilometers2degrees(distance_km),
        phase_list=["p", "P", "Pn", "Pg", "s", "S", "Sn", "Sg"],
    )
    p = min((a.time for a in arrivals if a.name.upper().startswith("P")), default=None)
    s = min((a.time for a in arrivals if a.name.upper().startswith("S")), default=None)
    return p, s


# ---- Network wrappers (thin; mocked in tests) ----------------------------------------

def _client():
    from obspy.clients.fdsn import Client

    return Client(FDSN_PROVIDER, timeout=HTTP_TIMEOUT)


def _with_retry(fn, what: str):
    from obspy.clients.fdsn.header import FDSNNoDataException

    last_error: Exception | None = None
    for _ in range(2):  # one retry
        try:
            return fn()
        except FDSNNoDataException as e:
            raise InsufficientDataError(f"No {what} available") from e
        except Exception as e:  # network errors, timeouts, server errors
            last_error = e
    raise UpstreamError(f"FDSN data service unavailable ({what})") from last_error


def fetch_nearby_channels(lat: float, lon: float, time: UTCDateTime) -> list[ChannelInfo]:
    t = UTCDateTime(time)
    try:
        inventory = _with_retry(
            lambda: _client().get_stations(
                latitude=lat, longitude=lon, maxradius=STATION_RADIUS_DEG,
                channel="HH?,BH?", level="channel", starttime=t, endtime=t + POST_P_SECONDS,
            ),
            "station metadata",
        )
    except InsufficientDataError:
        return []
    return [
        ChannelInfo(net.code, sta.code, cha.location_code, cha.code, cha.latitude, cha.longitude)
        for net in inventory for sta in net for cha in sta
    ]


def fetch_station_coords(network: str, station: str) -> tuple[float, float]:
    try:
        inventory = _with_retry(
            lambda: _client().get_stations(network=network, station=station, level="station"),
            "station metadata",
        )
    except InsufficientDataError as e:
        raise NotFoundError(f"Unknown station {network}.{station}") from e
    sta = inventory[0][0]
    return sta.latitude, sta.longitude


def fetch_waveform(network: str, station: str, location: str, band: str,
                   start: UTCDateTime, end: UTCDateTime) -> Stream:
    loc = location or "--"
    stream = _with_retry(
        lambda: _client().get_waveforms(network, station, loc, f"{band}?", start, end),
        "waveform data",
    )
    if any(tr.stats.channel[-1] in "12" for tr in stream):
        inventory = _with_retry(
            lambda: _client().get_stations(
                network=network, station=station, location=loc, channel=f"{band}?",
                starttime=start, endtime=end, level="channel",
            ),
            "channel metadata",
        )
        stream = orient_to_zne(stream, inventory)
    return stream
