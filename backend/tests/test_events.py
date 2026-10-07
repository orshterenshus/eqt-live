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


def test_invalid_json_retried_and_becomes_upstream_error(monkeypatch):
    calls = []

    def bad_json(url, params, timeout):
        calls.append(1)
        # Return 200 but with non-JSON content
        return httpx.Response(200, content=b"<html>", request=httpx.Request("GET", events.USGS_URL))

    monkeypatch.setattr(events.httpx, "get", bad_json)
    with pytest.raises(UpstreamError):
        events.fetch_recent()
    assert len(calls) == 2


def test_fetch_recent_with_400_becomes_upstream_error(monkeypatch):
    calls = []

    def bad_request(url, params, timeout):
        calls.append(1)
        return _response(400)

    monkeypatch.setattr(events.httpx, "get", bad_request)
    with pytest.raises(UpstreamError):
        events.fetch_recent()
    assert len(calls) == 2


def test_fetch_event_with_404_raises_not_found_once(monkeypatch):
    calls = []

    def not_found(url, params, timeout):
        calls.append(1)
        return _response(404)

    monkeypatch.setattr(events.httpx, "get", not_found)
    with pytest.raises(NotFoundError):
        events.fetch_event("nope")
    assert len(calls) == 1  # Should NOT retry


def test_fetch_event_null_magnitude_raises_not_found(monkeypatch):
    monkeypatch.setattr(events.httpx, "get", lambda url, params, timeout: _response(200, json=NO_MAG))
    with pytest.raises(NotFoundError, match="no magnitude"):
        events.fetch_event("nomag")


def test_fetch_event_malformed_payload_raises_upstream_error(monkeypatch):
    calls = []

    def bad_payload(url, params, timeout):
        calls.append(1)
        # Return valid JSON with mag but missing geometry coordinates
        return httpx.Response(200, json={"type": "Feature", "id": "test", "properties": {"mag": 5.0}, "geometry": {"type": "Point", "coordinates": []}}, request=httpx.Request("GET", events.USGS_URL))

    monkeypatch.setattr(events.httpx, "get", bad_payload)
    with pytest.raises(UpstreamError, match="unexpected"):
        events.fetch_event("bad")


def test_5xx_then_success_returns_events(monkeypatch):
    calls = []

    def flaky(url, params, timeout):
        calls.append(1)
        if len(calls) == 1:
            return _response(503)
        return _response(200, json=FEED)

    monkeypatch.setattr(events.httpx, "get", flaky)
    result = events.fetch_recent()
    assert len(result) == 1
    assert len(calls) == 2


def test_fetch_recent_with_wrong_shape_raises_upstream_error(monkeypatch):
    """Missing 'features' key in response"""
    monkeypatch.setattr(
        events.httpx, "get",
        lambda url, params, timeout: _response(200, json={"error": "x"})
    )
    with pytest.raises(UpstreamError, match="unexpected"):
        events.fetch_recent()


def test_fetch_recent_missing_geometry_raises_upstream_error(monkeypatch):
    """Feature without geometry"""
    bad_feed = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "id": "bad", "properties": {"mag": 5.0}}]
    }
    monkeypatch.setattr(
        events.httpx, "get",
        lambda url, params, timeout: _response(200, json=bad_feed)
    )
    with pytest.raises(UpstreamError, match="unexpected"):
        events.fetch_recent()


def test_fetch_event_non_dict_body_raises_upstream_error(monkeypatch):
    """Body is a list instead of dict"""
    monkeypatch.setattr(
        events.httpx, "get",
        lambda url, params, timeout: _response(200, json=[])
    )
    with pytest.raises(UpstreamError, match="unexpected"):
        events.fetch_event("bad")


def test_fetch_event_null_properties_raises_upstream_error(monkeypatch):
    """Properties field is null"""
    monkeypatch.setattr(
        events.httpx, "get",
        lambda url, params, timeout: _response(
            200,
            json={
                "type": "Feature",
                "properties": None,
                "geometry": {"type": "Point", "coordinates": [1, 2, 3]}
            }
        )
    )
    with pytest.raises(UpstreamError, match="unexpected"):
        events.fetch_event("bad")


def test_fetch_event_400_not_retried(monkeypatch):
    """400 error immediately raises NotFoundError, no retry"""
    calls = []

    def bad(url, params, timeout):
        calls.append(1)
        return _response(400)

    monkeypatch.setattr(events.httpx, "get", bad)
    with pytest.raises(NotFoundError):
        events.fetch_event("nope")
    assert len(calls) == 1


def test_http_timeout_passed_to_httpx(monkeypatch):
    """Verify HTTP_TIMEOUT is passed to httpx.get"""
    seen_timeout = []

    def capture(url, params, timeout):
        seen_timeout.append(timeout)
        return _response(200, json=FEED)

    monkeypatch.setattr(events.httpx, "get", capture)
    events.fetch_recent()
    assert seen_timeout[0] == events.HTTP_TIMEOUT
