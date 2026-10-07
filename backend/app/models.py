"""Load the teacher and student models once and run batched inference."""
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.config import STUDENT_PATH, TEACHER_PATH, WINDOW
from app.errors import ModelsNotLoadedError

# Channel order each model expects. Windows arrive in ZNE order and are reordered in predict().
# Measured with scripts/check_channel_order.py on 5 held-out STEAD events (mean abs error):
#   teacher ZNE: P 8.0 ms, S 181.7 ms, det 1.00 | teacher ENZ: P 8.0 ms, S 137.7 ms, det 1.00
#   student ZNE: P 8.0 ms, S 155.7 ms, det 1.00 | student ENZ: P 8.0 ms, S 104.3 ms, det 1.00
# P and detection tie; ENZ gives lower S error for both models (small sample, modest margin).
CHANNEL_ORDER = {"teacher": "ENZ", "student": "ENZ"}


def reorder(windows: np.ndarray, order: str) -> np.ndarray:
    """Reorder the last axis of ZNE windows into `order` (e.g. 'ENZ')."""
    return windows[:, :, ["ZNE".index(c) for c in order]]


@dataclass
class ModelOutput:
    detection: np.ndarray  # (n_windows, 6000)
    p: np.ndarray
    s: np.ndarray
    latency_ms: float  # per window


class ModelRunner:
    def __init__(self):
        self.models: dict = {}
        self.paths: dict[str, Path] = {}

    @property
    def loaded(self) -> bool:
        return {"teacher", "student"} <= self.models.keys()

    def load(self, teacher_path: Path = TEACHER_PATH, student_path: Path = STUDENT_PATH) -> None:
        import tensorflow as tf

        from app.eqt_layers import CUSTOM_OBJECTS

        self.models["teacher"] = tf.keras.models.load_model(
            teacher_path, custom_objects=CUSTOM_OBJECTS, compile=False
        )
        self.models["student"] = tf.keras.models.load_model(student_path, compile=False)
        self.paths = {"teacher": Path(teacher_path), "student": Path(student_path)}
        warmup = np.zeros((1, WINDOW, 3), np.float32)
        for name in self.models:
            self.predict(name, warmup)  # first call builds the graph; keep it out of timings

    def predict(self, name: str, windows: np.ndarray) -> ModelOutput:
        if not self.loaded:
            raise ModelsNotLoadedError("Models are not loaded")
        x = reorder(windows.astype(np.float32), CHANNEL_ORDER[name])
        start = time.perf_counter()
        outputs = self.models[name](x, training=False)
        elapsed_ms = (time.perf_counter() - start) * 1000
        detection, p, s = (np.asarray(o)[..., 0] for o in outputs)
        return ModelOutput(detection, p, s, latency_ms=elapsed_ms / len(windows))

    def info(self) -> dict:
        if not self.loaded:
            raise ModelsNotLoadedError("Models are not loaded")
        result = {
            name: {
                "name": name,
                "params": int(self.models[name].count_params()),
                "size_mb": round(self.paths[name].stat().st_size / 2**20, 2),
            }
            for name in ("teacher", "student")
        }
        result["compression"] = round(result["teacher"]["params"] / result["student"]["params"], 2)
        return result
