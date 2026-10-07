from pathlib import Path

import numpy as np
import pytest

from app.errors import ModelsNotLoadedError
from app.models import ModelRunner
from app.preprocess import standardize

FIXTURE = Path(__file__).parent / "fixtures" / "stead_samples.npz"


@pytest.fixture(scope="module")
def runner():
    r = ModelRunner()
    r.load()
    return r


@pytest.fixture(scope="module")
def stead():
    d = np.load(FIXTURE)
    windows = np.stack([standardize(w).T for w in d["waves"]])
    return windows, d["p"], d["s"]


@pytest.mark.parametrize("name", ["teacher", "student"])
def test_output_shapes(runner, stead, name):
    windows = stead[0]
    out = runner.predict(name, windows)
    assert out.detection.shape == out.p.shape == out.s.shape == (len(windows), 6000)
    assert out.latency_ms > 0


@pytest.mark.parametrize("name", ["teacher", "student"])
def test_p_picks_match_catalog_on_stead(runner, stead, name):
    windows, p_true, _ = stead
    out = runner.predict(name, windows)
    errors = np.abs(out.p.argmax(axis=1) - p_true)
    assert np.sum(errors <= 50) >= len(p_true) - 1  # within 0.5 s for at least 4 of 5


def test_predict_before_load_raises():
    with pytest.raises(ModelsNotLoadedError):
        ModelRunner().predict("student", np.zeros((1, 6000, 3), np.float32))


def test_info_reports_sizes_and_compression(runner):
    info = runner.info()
    assert info["student"]["params"] == 60659
    assert info["teacher"]["params"] > 300_000
    assert 5.5 < info["compression"] < 6.5
    assert info["student"]["size_mb"] < 1


@pytest.mark.parametrize("name", ["teacher", "student"])
def test_latency_reported_and_steady_state_not_slower(runner, stead, name):
    windows = stead[0][:3]
    runner.predict(name, windows)  # ensure steady state
    first = runner.predict(name, windows).latency_ms
    second = runner.predict(name, windows).latency_ms
    assert first > 0 and second > 0
    assert second < 5 * first  # generous bound: catches retracing/regressions, not noise
