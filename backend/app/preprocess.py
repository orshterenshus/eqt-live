"""Turn raw 3-component waveforms into model-ready windows.

Mirrors the training pipeline (EQ_Project/kd_framework/data.py): 100 Hz,
6000-sample windows, per-channel standardization, no extra filtering.
"""
import numpy as np
from scipy.signal import resample

from app.config import SAMPLING_RATE, STRIDE, WINDOW
from app.errors import InsufficientDataError


def resample_to(data: np.ndarray, fs: float, target_fs: float = SAMPLING_RATE) -> np.ndarray:
    """Resample a (3, N) array from fs to target_fs."""
    if fs == target_fs:
        return data.astype(np.float32)
    n_out = int(round(data.shape[1] * target_fs / fs))
    return resample(data, n_out, axis=1).astype(np.float32)


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
