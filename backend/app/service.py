"""Orchestration: fetch data, run both models, build the API response."""
import logging
from datetime import timezone

import numpy as np
from obspy import UTCDateTime
from obspy.geodetics import gps2dist_azimuth

from app import events, stations
from app.cache import ResultCache
from app.config import (
    LIVE_DELAY_SECONDS, LIVE_SECONDS, LIVE_STATIONS, POST_P_SECONDS, PRE_P_SECONDS, SAMPLING_RATE,
)
from app.errors import NotFoundError
from app.picks import downsample, extract_picks, stitch
from app.preprocess import filter_waveform, make_windows, resample_to, standardize
from app.schemas import AnalysisResult, Curves, ModelResult, Theoretical, Waveform

log = logging.getLogger("eqt_live")


def _to_dt(t: UTCDateTime):
    return t.datetime.replace(tzinfo=timezone.utc)


def _rounded(x: np.ndarray) -> list[float]:
    return np.round(x.astype(float), 3).tolist()


def _model_result(runner, name: str, windows, starts, start: UTCDateTime) -> ModelResult:
    out = runner.predict(name, windows)
    det, p, s = (stitch(c, starts) for c in (out.detection, out.p, out.s))
    picks = extract_picks(det, p, s)

    def at(index):
        return None if index is None else _to_dt(start + index / SAMPLING_RATE)

    return ModelResult(
        detected=picks.detected,
        detection_max=round(picks.detection_max, 3),
        p_time=at(picks.p_index),
        s_time=at(picks.s_index),
        p_conf=None if picks.p_conf is None else round(picks.p_conf, 3),
        s_conf=None if picks.s_conf is None else round(picks.s_conf, 3),
        latency_ms=round(out.latency_ms, 2),
        curves=Curves(**{k: _rounded(downsample(v)[0]) for k, v in
                         (("detection", det), ("p", p), ("s", s))}),
    )


def analyze_array(runner, data: np.ndarray, fs: float, start: UTCDateTime, station_id: str,
                  distance_km: float | None = None, theoretical_p: UTCDateTime | None = None,
                  theoretical_s: UTCDateTime | None = None) -> AnalysisResult:
    data = filter_waveform(data, fs)
    windows, starts = make_windows(data, fs)
    teacher = _model_result(runner, "teacher", windows, starts, start)
    student = _model_result(runner, "student", windows, starts, start)
    display = standardize(resample_to(data, fs))
    z, step = downsample(display[0])
    log.info("analysis station=%s teacher_ms=%.1f student_ms=%.1f detected=%s/%s",
             station_id, teacher.latency_ms, student.latency_ms, teacher.detected, student.detected)
    return AnalysisResult(
        station=station_id,
        distance_km=distance_km,
        start_time=_to_dt(start),
        display_dt=step / SAMPLING_RATE,
        waveform=Waveform(z=_rounded(z), n=_rounded(display[1][::step]),
                          e=_rounded(display[2][::step])),
        theoretical=Theoretical(
            p_time=_to_dt(theoretical_p) if theoretical_p else None,
            s_time=_to_dt(theoretical_s) if theoretical_s else None,
        ),
        teacher=teacher,
        student=student,
    )


def list_stations(event_id: str) -> list[stations.StationInfo]:
    event = events.fetch_event(event_id)
    origin = UTCDateTime(event.time.timestamp())
    channels = stations.fetch_nearby_channels(event.lat, event.lon, origin)
    return stations.select_stations(channels, event.lat, event.lon)


def analyze_event(runner, event_id: str, station_id: str) -> AnalysisResult:
    net, sta, loc, band = stations.parse_station_id(station_id)
    event = events.fetch_event(event_id)
    slat, slon = stations.fetch_station_coords(net, sta)
    distance_km = round(gps2dist_azimuth(event.lat, event.lon, slat, slon)[0] / 1000, 1)
    origin = UTCDateTime(event.time.timestamp())
    p_travel, s_travel = stations.theoretical_arrivals(distance_km, event.depth_km)
    p_time = origin + p_travel if p_travel is not None else None
    s_time = origin + s_travel if s_travel is not None else None
    window_start = (p_time or origin) - PRE_P_SECONDS
    window_end = (p_time or origin) + POST_P_SECONDS
    stream = stations.fetch_waveform(net, sta, loc, band, window_start, window_end)
    data, fs, start = stations.stream_to_array(stream)
    return analyze_array(runner, data, fs, start, station_id, distance_km, p_time, s_time)


def analyze_live(runner, station_id: str, cache: ResultCache) -> AnalysisResult:
    if station_id not in dict(LIVE_STATIONS):
        raise NotFoundError(f"'{station_id}' is not one of the live stations")
    net, sta, loc, band = stations.parse_station_id(station_id)
    now = UTCDateTime()
    end = UTCDateTime(int((now.timestamp - LIVE_DELAY_SECONDS) // 60 * 60))  # whole minute
    start = end - LIVE_SECONDS

    def compute():
        stream = stations.fetch_waveform(net, sta, loc, band, start, end)
        data, fs, data_start = stations.stream_to_array(stream)
        return analyze_array(runner, data, fs, data_start, station_id)

    return cache.get_or_compute(("live", station_id, end.timestamp), compute)
