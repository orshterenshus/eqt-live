from datetime import timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient
from obspy import Stream, Trace, UTCDateTime

from app import events, stations
from app.errors import ModelsNotLoadedError, UpstreamError
from app.events import Event
from app.main import create_app
from app.models import ModelOutput

ORIGIN = UTCDateTime(2026, 10, 7, 12, 0, 0)
EVENT = Event("us1", ORIGIN.datetime.replace(tzinfo=timezone.utc), 5.0, 35.0, 139.0, 10.0, "Japan")
STATION = "IU.MAJO.00.BH"


class FakeRunner:
    loaded = True

    def predict(self, name, windows):
        n = len(windows)
        det = np.full((n, 6000), 0.9, np.float32)
        p = np.zeros((n, 6000), np.float32)
        p[:, 3000] = 0.8
        s = np.zeros((n, 6000), np.float32)
        s[:, 4000] = 0.7
        return ModelOutput(det, p, s, latency_ms=10.0 if name == "teacher" else 2.0)

    def info(self):
        return {
            "teacher": {"name": "teacher", "params": 373495, "size_mb": 4.85},
            "student": {"name": "student", "params": 60659, "size_mb": 0.39},
            "compression": 6.16,
        }


class NotLoadedRunner(FakeRunner):
    loaded = False

    def predict(self, name, windows):
        raise ModelsNotLoadedError("Models are not loaded")


def fake_stream(start, end):
    n = int((end - start) * 100)
    rng = np.random.default_rng(0)
    return Stream([
        Trace(rng.normal(size=n), header={"network": "IU", "station": "MAJO", "location": "00",
                                          "channel": f"BH{c}", "sampling_rate": 100.0,
                                          "starttime": start})
        for c in "ZNE"
    ])


@pytest.fixture
def waveform_calls(monkeypatch):
    calls = []

    def fetch_waveform(net, sta, loc, band, start, end):
        calls.append((net, sta, start))
        return fake_stream(start, end)

    monkeypatch.setattr(events, "fetch_event", lambda event_id: EVENT)
    monkeypatch.setattr(events, "fetch_recent", lambda days, min_mag: [EVENT])
    monkeypatch.setattr(stations, "fetch_station_coords", lambda net, sta: (35.5, 139.5))
    monkeypatch.setattr(stations, "fetch_nearby_channels", lambda lat, lon, time: [
        stations.ChannelInfo("IU", "MAJO", "00", f"BH{c}", 35.5, 139.5) for c in "ZNE"
    ])
    monkeypatch.setattr(stations, "fetch_waveform", fetch_waveform)
    return calls


@pytest.fixture
def client(waveform_calls):
    with TestClient(create_app(runner=FakeRunner(), load_models=False)) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "models_loaded": True}


def test_events(client):
    body = client.get("/api/events", params={"days": 2, "min_mag": 4}).json()
    assert body[0]["id"] == "us1" and body[0]["magnitude"] == 5.0


def test_events_validates_params(client):
    r = client.get("/api/events", params={"days": 30})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "invalid_request"
    assert isinstance(body["message"], str) and body["message"]


def test_missing_param_uses_error_shape(client):
    r = client.get("/api/analyze", params={"event_id": "us1"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "invalid_request"
    assert "station" in body["message"]


def test_unexpected_error_is_500_json(waveform_calls, monkeypatch):
    def boom(days, min_mag):
        raise RuntimeError("boom")

    monkeypatch.setattr(events, "fetch_recent", boom)
    app = create_app(runner=FakeRunner(), load_models=False)
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/events")
    assert r.status_code == 500
    assert r.json() == {"error": "internal_error", "message": "Internal server error"}


def test_too_short_stream_is_422(client, monkeypatch):
    monkeypatch.setattr(stations, "fetch_waveform", lambda *a: fake_stream(a[4], a[4] + 0.1))
    r = client.get("/api/analyze", params={"event_id": "us1", "station": STATION})
    assert r.status_code == 422 and r.json()["error"] == "insufficient_data"


def test_stations(client):
    body = client.get("/api/events/us1/stations").json()
    assert body[0]["id"] == STATION and body[0]["distance_km"] > 0


def test_analyze_returns_both_models(client):
    r = client.get("/api/analyze", params={"event_id": "us1", "station": STATION})
    assert r.status_code == 200
    body = r.json()
    assert body["teacher"]["detected"] and body["student"]["detected"]
    assert body["student"]["latency_ms"] == 2.0
    assert body["student"]["p_time"] is not None
    assert body["theoretical"]["p_time"] is not None
    assert len(body["waveform"]["z"]) <= 3000
    assert len(body["waveform"]["z"]) == len(body["student"]["curves"]["p"])


def test_analyze_is_cached(client, waveform_calls):
    for _ in range(2):
        client.get("/api/analyze", params={"event_id": "us1", "station": STATION})
    assert len(waveform_calls) == 1


def test_bad_station_id_is_422(client):
    r = client.get("/api/analyze", params={"event_id": "us1", "station": "bad"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_request"


def test_upstream_failure_is_502(client, monkeypatch):
    def boom(event_id):
        raise UpstreamError("USGS earthquake service unavailable")

    monkeypatch.setattr(events, "fetch_event", boom)
    r = client.get("/api/analyze", params={"event_id": "other", "station": STATION})
    assert r.status_code == 502 and "USGS" in r.json()["message"]


def test_live_stations_and_live(client):
    stations_list = client.get("/api/live/stations").json()
    assert len(stations_list) == 8
    r = client.get("/api/live", params={"station": stations_list[0]["id"]})
    assert r.status_code == 200
    assert r.json()["theoretical"]["p_time"] is None


def test_live_rejects_unknown_station(client):
    assert client.get("/api/live", params={"station": "XX.NOPE.00.BH"}).status_code == 404


def test_models_info(client):
    assert client.get("/api/models").json()["compression"] == 6.16


def test_models_not_loaded(waveform_calls):
    with TestClient(create_app(runner=NotLoadedRunner(), load_models=False)) as c:
        assert c.get("/health").json()["models_loaded"] is False
        r = c.get("/api/analyze", params={"event_id": "us1", "station": STATION})
        assert r.status_code == 503
