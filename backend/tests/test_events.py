import httpx
import pytest

from app import events
from app.errors import NotFoundError, UpstreamError

FEATURE = {
    "type": "Feature",
    "id": "us7000abcd",
    "properties": {"mag": 5.2, "place": "10 km N of Somewhere, Japan", "time": 1791374400000},
    "geometry": {"type": "Point", "coordinates": [142.5, 38.1, 35.0]},
}
NO_MAG = {**FEATURE, "id": "nomag", "properties": {**FEATURE["properties"], "mag": None}}
FEED = {"type": "FeatureCollection", "features": [FEATURE, NO_MAG]}


def _response(status, json=None):
    return httpx.Response(status, json=json, request=httpx.Request("GET", events.USGS_URL))


def test_parse_feature():
    e = events.parse_feature(FEATURE)
    assert e.id == "us7000abcd" and e.magnitude == 5.2
    assert (e.lat, e.lon, e.depth_km) == (38.1, 142.5, 35.0)
    assert e.time.isoformat() == "2026-10-07T12:00:00+00:00"


def test_parse_feed_skips_events_without_magnitude():
    assert [e.id for e in events.parse_feed(FEED)] == ["us7000abcd"]


def test_fetch_recent_sends_filters(monkeypatch):
    seen = {}

    def fake_get(url, params, timeout):
        seen.update(params)
        return _response(200, FEED)

    monkeypatch.setattr(events.httpx, "get", fake_get)
    result = events.fetch_recent(days=2, min_mag=4.5)
    assert len(result) == 1
    assert seen["minmagnitude"] == 4.5 and seen["format"] == "geojson"


def test_fetch_event_not_found(monkeypatch):
    monkeypatch.setattr(events.httpx, "get", lambda url, params, timeout: _response(404))
    with pytest.raises(NotFoundError):
        events.fetch_event("nope")


def test_timeout_becomes_upstream_error_after_one_retry(monkeypatch):
    calls = []

    def boom(url, params, timeout):
        calls.append(1)
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(events.httpx, "get", boom)
    with pytest.raises(UpstreamError):
        events.fetch_recent()
    assert len(calls) == 2
