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


def test_background_load_makes_requests_wait_instead_of_failing():
    r = ModelRunner()
    r.start_background_load()
    assert r.loading and not r.loaded
    out = r.predict("student", np.zeros((1, 6000, 3), np.float32))  # blocks until loaded
    assert r.loaded and not r.loading
    assert out.detection.shape == (1, 6000)


def test_failed_background_load_raises_not_loaded(tmp_path):
    r = ModelRunner()
    r.load = lambda: (_ for _ in ()).throw(OSError("missing model file"))
    r.start_background_load()
    with pytest.raises(ModelsNotLoadedError):
        r.predict("student", np.zeros((1, 6000, 3), np.float32))
    assert not r.loading


def test_info_reports_sizes_and_compression(runner):
    info = runner.info()
    assert info["student"]["params"] == 60659
    assert info["teacher"]["params"] > 300_000
    assert 5.5 < info["compression"] < 6.5
    assert info["student"]["size_mb"] < 1


@pytest.mark.parametrize("name", ["teacher", "student"])
def test_compiled_function_traces_once(runner, stead, name):
    windows = stead[0]
    for n in (1, 3):
        assert runner.predict(name, windows[:n]).latency_ms > 0
    # Fixed input_signature: every batch size shares one trace (no eager fallback, no retracing).
    assert runner._compiled[name].experimental_get_tracing_count() == 1


@pytest.mark.parametrize("name", ["teacher", "student"])
def test_predictions_are_deterministic(runner, stead, name):
    # The stock teacher keeps Monte-Carlo dropout on; the runner must switch it off.
    windows = stead[0]
    a, b = runner.predict(name, windows), runner.predict(name, windows)
    for x, y in ((a.detection, b.detection), (a.p, b.p), (a.s, b.s)):
        np.testing.assert_array_equal(x, y)


def test_teacher_gets_enz_and_student_zne():
    from app.models import CHANNEL_ORDER, reorder

    assert CHANNEL_ORDER == {"teacher": "ENZ", "student": "ZNE"}
    zne = np.arange(3, dtype=np.float32).reshape(1, 1, 3)  # Z=0, N=1, E=2
    assert reorder(zne, "ENZ")[0, 0].tolist() == [2.0, 1.0, 0.0]
