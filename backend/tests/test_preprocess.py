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


def _rms(x):
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def _sine(freq, fs, seconds=120):
    t = np.arange(int(fs * seconds)) / fs
    return np.tile(np.sin(2 * np.pi * freq * t), (3, 1))


def test_filter_waveform_removes_microseism():
    from app.preprocess import filter_waveform
    out = filter_waveform(_sine(0.2, 100.0), 100.0)
    mid = slice(3000, -3000)
    assert _rms(out[:, mid]) < 0.1 * _rms(_sine(0.2, 100.0)[:, mid])


def test_filter_waveform_keeps_passband():
    from app.preprocess import filter_waveform
    x = _sine(5.0, 100.0)
    out = filter_waveform(x, 100.0)
    mid = slice(3000, -3000)
    assert _rms(out[:, mid]) > 0.8 * _rms(x[:, mid])


def test_filter_waveform_40hz_uses_highpass_only():
    from app.preprocess import filter_waveform
    x = _sine(5.0, 40.0) + 3.0  # offset is removed by demean
    out = filter_waveform(x, 40.0)
    assert out.shape == x.shape and out.dtype == np.float32
    assert np.all(np.isfinite(out)) and abs(out[:, 2000:-2000].mean()) < 0.05


def test_filter_waveform_shape_dtype():
    from app.preprocess import filter_waveform
    out = filter_waveform(np.random.default_rng(0).normal(size=(3, 6000)), 100.0)
    assert out.shape == (3, 6000) and out.dtype == np.float32
