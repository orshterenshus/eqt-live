import numpy as np
import pytest

from app.errors import InsufficientDataError
from app.preprocess import make_windows, resample_to, standardize, window_starts


def test_standardize_gives_zero_mean_unit_std_per_channel():
    rng = np.random.default_rng(0)
    x = rng.normal(5.0, 3.0, size=(3, 6000)) * np.array([[1.0], [10.0], [100.0]])
    out = standardize(x)
    assert out.dtype == np.float32
    assert np.allclose(out.mean(axis=1), 0, atol=1e-4)
    assert np.allclose(out.std(axis=1), 1, atol=1e-4)


def test_standardize_leaves_flat_channel_at_zero():
    x = np.ones((3, 100))
    x[0] = np.arange(100)
    out = standardize(x)
    assert np.all(out[1] == 0) and np.all(out[2] == 0)


def test_resample_40hz_to_100hz():
    out = resample_to(np.zeros((3, 4000), np.float32), 40.0)
    assert out.shape == (3, 10000)


def test_resample_noop_at_100hz():
    data = np.ones((3, 500), np.float32)
    assert resample_to(data, 100.0).shape == (3, 500)


def test_window_starts_cover_end_of_trace():
    assert window_starts(6000) == [0]
    assert window_starts(12000) == [0, 3000, 6000]
    assert window_starts(13000) == [0, 3000, 6000, 7000]


def test_window_starts_rejects_short_trace():
    with pytest.raises(InsufficientDataError):
        window_starts(5999)


def test_make_windows_shape_and_channels_last():
    data = np.zeros((3, 12000), np.float32)
    data[0] = 1.0
    data[0, ::2] = -1.0  # Z alternates -1/+1 -> stays +-1 after z-score
    windows, starts = make_windows(data, 100.0)
    assert windows.shape == (3, 6000, 3)
    assert starts == [0, 3000, 6000]
    assert np.allclose(np.abs(windows[0, :, 0]), 1.0)  # Z is channel 0
    assert np.all(windows[0, :, 1] == 0)


def test_make_windows_rejects_wrong_channel_count():
    with pytest.raises(InsufficientDataError):
        make_windows(np.zeros((2, 7000)), 100.0)
