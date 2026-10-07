"""Load the teacher and student models once and run batched inference."""
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.config import STUDENT_PATH, TEACHER_PATH, WINDOW
from app.errors import ModelsNotLoadedError

# Channel order each model expects. Windows arrive in ZNE order and are reordered in predict().
# Measured with scripts/check_channel_order.py on 200 held-out STEAD events
# (P mean/median error, fraction of P picks within 0.5 s, S mean/median error):
#   teacher ZNE: P 11.6/0.0 ms, 0.99 | S 310.6/60.0 ms    teacher ENZ: P 32.2/0.0 ms, 0.97 | S 129.6/41.5 ms
#   student ZNE: P 32.6/0.0 ms, 0.97 | S 218.2/40.0 ms    student ENZ: P 33.1/0.0 ms, 0.97 | S 253.7/45.0 ms
# ENZ is not clearly better for either model (teacher ENZ has worse P), so keep ZNE (training order).
CHANNEL_ORDER = {"teacher": "ZNE", "student": "ZNE"}

# FastAPI runs sync endpoints in a threadpool; without this lock two concurrent requests would
# compete for the same CPU cores and inflate each other's measured latency.
_INFERENCE_LOCK = threading.Lock()
WARMUP_BATCH_SIZES = (1, 3)  # the app typically sends 3 windows


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
        self._compiled: dict = {}
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
        # A traced tf.function avoids eager-mode Python overhead (~30-100x faster on CPU).
        self._compiled = {
            name: tf.function(
                lambda x, m=model: m(x, training=False),
                input_signature=[tf.TensorSpec([None, WINDOW, 3], tf.float32)],
                reduce_retracing=True,
            )
            for name, model in self.models.items()
        }
        for name in self.models:
            for n in WARMUP_BATCH_SIZES:  # first calls trace/optimise; keep them out of timings
                self.predict(name, np.zeros((n, WINDOW, 3), np.float32))

    def predict(self, name: str, windows: np.ndarray) -> ModelOutput:
        if not self.loaded:
            raise ModelsNotLoadedError("Models are not loaded")
        x = reorder(windows.astype(np.float32), CHANNEL_ORDER[name])
        with _INFERENCE_LOCK:
            start = time.perf_counter()
            outputs = self._compiled[name](x)
            detection, p, s = (o.numpy()[..., 0] for o in outputs)
            elapsed_ms = (time.perf_counter() - start) * 1000
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
