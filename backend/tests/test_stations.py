import numpy as np
import pytest
from obspy import Stream, Trace, UTCDateTime

from app import stations
from app.errors import InsufficientDataError, InvalidRequestError
from app.stations import ChannelInfo


def ch(net, sta, loc, code, lat=35.0, lon=139.0):
    return ChannelInfo(net, sta, loc, code, lat, lon)


def test_select_stations_requires_three_components_and_sorts_by_distance():
    channels = [
        *(ch("IU", "FAR", "00", f"BH{c}", lat=37.0) for c in "ZNE"),
        *(ch("IU", "NEAR", "00", f"BH{c}", lat=35.1) for c in "ZNE"),
        ch("IU", "PART", "00", "BHZ"),
        ch("IU", "PART", "00", "BHN"),
    ]
    result = stations.select_stations(channels, 35.0, 139.0)
    assert [s.station for s in result] == ["NEAR", "FAR"]
    assert 10 < result[0].distance_km < 12
    assert result[0].id == "IU.NEAR.00.BH"


def test_select_stations_prefers_hh_over_bh():
    channels = [
        *(ch("JP", "ABC", "", f"BH{c}") for c in "ZNE"),
        *(ch("JP", "ABC", "", f"HH{c}") for c in "ZNE"),
    ]
    [only] = stations.select_stations(channels, 35.0, 139.0)
    assert only.band == "HH" and only.id == "JP.ABC..HH"


def test_parse_station_id():
    assert stations.parse_station_id("IU.ANMO.00.BH") == ("IU", "ANMO", "00", "BH")
    assert stations.parse_station_id("JP.ABC..HH") == ("JP", "ABC", "", "HH")
    with pytest.raises(InvalidRequestError):
        stations.parse_station_id("IU.ANMO")


def _trace(comp, n=1000, start=UTCDateTime(2026, 1, 1)):
    header = {"network": "IU", "station": "X", "location": "00", "channel": f"BH{comp}",
              "sampling_rate": 100.0, "starttime": start}
    return Trace(np.arange(n, dtype=np.float64), header=header)


def test_stream_to_array_orders_zne_and_trims_to_common_span():
    st = Stream([_trace("E"), _trace("N", start=UTCDateTime(2026, 1, 1, 0, 0, 1)), _trace("Z")])
    data, fs, start = stations.stream_to_array(st)
    assert data.shape == (3, 900)
    assert fs == 100.0
    assert start == UTCDateTime(2026, 1, 1, 0, 0, 1)


def test_stream_to_array_missing_channel():
    with pytest.raises(InsufficientDataError):
        stations.stream_to_array(Stream([_trace("Z"), _trace("N")]))


def test_theoretical_arrivals_at_100_km():
    p, s = stations.theoretical_arrivals(100.0, 10.0)
    assert 12 < p < 20
    assert 22 < s < 35
