"""Turn the models' probability curves into detections and P/S picks."""
import math
from dataclasses import dataclass

import numpy as np

from app.config import DETECTION_THRESHOLD, DISPLAY_POINTS, PICK_THRESHOLD, WINDOW


def stitch(curves: np.ndarray, starts: list[int]) -> np.ndarray:
    """Place each window's curve at its offset; overlapping samples keep the max."""
    out = np.zeros(starts[-1] + WINDOW, np.float32)
    for curve, start in zip(curves, starts):
        segment = out[start : start + WINDOW]
        np.maximum(segment, curve, out=segment)
    return out


@dataclass
class Picks:
    detected: bool
    detection_max: float
    p_index: int | None
    p_conf: float | None
    s_index: int | None
    s_conf: float | None


def _pick(curve: np.ndarray) -> tuple[int | None, float | None]:
    i = int(np.argmax(curve))
    conf = float(curve[i])
    return (i, conf) if conf >= PICK_THRESHOLD else (None, None)


def extract_picks(detection: np.ndarray, p: np.ndarray, s: np.ndarray) -> Picks:
    detection_max = float(detection.max())
    if detection_max < DETECTION_THRESHOLD:
        return Picks(False, detection_max, None, None, None, None)
    p_index, p_conf = _pick(p)
    s_index, s_conf = _pick(s)
    return Picks(True, detection_max, p_index, p_conf, s_index, s_conf)


def downsample(x: np.ndarray, max_points: int = DISPLAY_POINTS) -> tuple[np.ndarray, int]:
    step = max(1, math.ceil(len(x) / max_points))
    return x[::step], step
