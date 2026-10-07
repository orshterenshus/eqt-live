"""Turn raw 3-component waveforms into model-ready windows.

Windowing mirrors the training pipeline (EQ_Project/kd_framework/data.py): 100 Hz,
6000-sample windows, per-channel standardization. Real (non-STEAD) data is first passed
through filter_waveform, which mirrors EQTransformer's mseed_predictor preprocessing.
"""
import numpy as np
from scipy.signal import butter, resample, sosfiltfilt

from app.config import FILTER_FREQMAX, FILTER_FREQMIN, SAMPLING_RATE, STRIDE, WINDOW
from app.errors import InsufficientDataError


def resample_to(data: np.ndarray, fs: float, target_fs: float = SAMPLING_RATE) -> np.ndarray:
    """Resample a (3, N) array from fs to target_fs."""
    if fs == target_fs:
        return data.astype(np.float32)
    n_out = int(round(data.shape[1] * target_fs / fs))
    return resample(data, n_out, axis=1).astype(np.float32)


def filter_waveform(data: np.ndarray, fs: float) -> np.ndarray:
    """EqT-style conditioning of a (3, N) array: demean, zero-phase 1-45 Hz bandpass, taper.

    Equivalent to obspy detrend('demean') + bandpass(1, 45, corners=2, zerophase=True) +
    taper(max_percentage=0.001, max_length=2 s). obspy's zerophase applies an order-2 filter
    forwards and backwards, which is exactly sosfiltfilt with butter(2, ...). If 45 Hz is at
    or above Nyquist (e.g. 40 Hz data) only the 1 Hz high-pass is applied.
    """
    x = np.asarray(data, dtype=np.float64)
    x = x - x.mean(axis=1, keepdims=True)
    nyq = fs / 2.0
    if FILTER_FREQMAX >= nyq:
        sos = butter(2, FILTER_FREQMIN / nyq, btype="highpass", output="sos")
    else:
        sos = butter(2, [FILTER_FREQMIN / nyq, FILTER_FREQMAX / nyq], btype="bandpass",
                     output="sos")
    x = sosfiltfilt(sos, x, axis=1)
    n_taper = min(int(0.001 * x.shape[1]), int(2 * fs))
    if n_taper > 1:
        ramp = 0.5 * (1 - np.cos(np.pi * np.arange(n_taper) / n_taper))
        x[:, :n_taper] *= ramp
        x[:, -n_taper:] *= ramp[::-1]
    return x.astype(np.float32)


def standardize(window: np.ndarray) -> np.ndarray:
    """Per-channel (x - mean) / std. Flat channels become zeros."""
    out = window.astype(np.float32, copy=True)
    for ch in range(out.shape[0]):
        out[ch] -= out[ch].mean()
        std = out[ch].std()
        if std > 0:
            out[ch] /= std
    return out


def window_starts(n_samples: int) -> list[int]:
    """Start offsets of 6000-sample windows with 3000 stride; the last one ends at the trace end."""
    if n_samples < WINDOW:
        seconds = n_samples / SAMPLING_RATE
        raise InsufficientDataError(
            f"Need at least {WINDOW / SAMPLING_RATE:.0f} s of data, got {seconds:.1f} s"
        )
    starts = list(range(0, n_samples - WINDOW + 1, STRIDE))
    if starts[-1] != n_samples - WINDOW:
        starts.append(n_samples - WINDOW)
    return starts


def make_windows(data: np.ndarray, fs: float) -> tuple[np.ndarray, list[int]]:
    """(3, N) Z/N/E array at fs -> ((n_windows, 6000, 3) array, start offsets at 100 Hz)."""
    if data.ndim != 2 or data.shape[0] != 3:
        raise InsufficientDataError("Expected 3 channels (Z, N, E)")
    resampled = resample_to(data, fs)
    starts = window_starts(resampled.shape[1])
    windows = np.stack([standardize(resampled[:, s : s + WINDOW]).T for s in starts])
    return windows, starts
