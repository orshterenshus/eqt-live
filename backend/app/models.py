"""Load the teacher and student models once and run batched inference."""
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.config import STUDENT_PATH, TEACHER_PATH, WINDOW
from app.errors import ModelsNotLoadedError

# Channel order each model expects. Windows arrive in ZNE order and are reordered in predict().
# The teacher was trained on STEAD in E,N,Z order (channel 0 = E, as in EQTransformer's own
# plotting code); the student was trained on ZNE. Measured in the thesis project on 800 held-out
# STEAD events with the teacher made deterministic (see TEACHER_DETERMINISTIC):
#   teacher ZNE: P 35.8 ms, S 162.4 ms MAE (S within 0.1 s: 67.9%)
#   teacher ENZ: P 22.1 ms, S  83.8 ms MAE (S within 0.1 s: 80.6%)
# An earlier 200-event check here preferred ZNE, but it ran the teacher with dropout still on,
# so its numbers were noisy.
CHANNEL_ORDER = {"teacher": "ENZ", "student": "ZNE"}

# EQTransformer hard-codes SpatialDropout1D(training=True) (Monte-Carlo dropout), so the stock
# teacher returns different curves on every call. Zeroing the dropout rates after loading makes
# it deterministic, which a fair side-by-side comparison needs.
TEACHER_DETERMINISTIC = True

# FastAPI runs sync endpoints in a threadpool; without this lock two concurrent requests would
# compete for the same CPU cores and inflate each other's measured latency.
_INFERENCE_LOCK = threading.Lock()
WARMUP_BATCH_SIZES = (1, 3)  # the app typically sends 3 windows
# After a cold start the models load in the background (~1 min on 1 vCPU); requests that need
# them wait this long instead of failing, which stays under Cloud Run's 120 s request timeout.
LOAD_WAIT_S = 100

log = logging.getLogger("eqt_live")


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
        self._ready = False
        self._loading = threading.Event()  # set while a background load is running
        self._done = threading.Event()  # set when the background load finished (ok or failed)

    @property
    def loaded(self) -> bool:
        return self._ready

    @property
    def loading(self) -> bool:
        return self._loading.is_set()

    def start_background_load(self) -> None:
        """Load in a daemon thread so the server answers (and serves the page) immediately."""
        if self._ready or self._loading.is_set():
            return
        self._loading.set()
        self._done.clear()

        def run():
            try:
                self.load()
                log.info("Models loaded")
            except Exception:
                log.exception("Model loading failed")
            finally:
                self._loading.clear()
                self._done.set()

        threading.Thread(target=run, name="model-loader", daemon=True).start()

    def _wait_for_load(self) -> None:
        if not self._ready and self._loading.is_set():
            self._done.wait(LOAD_WAIT_S)
        if not self._ready:
            raise ModelsNotLoadedError("Models are not loaded")

    def load(self, teacher_path: Path = TEACHER_PATH, student_path: Path = STUDENT_PATH) -> None:
        import tensorflow as tf

        from app.eqt_layers import CUSTOM_OBJECTS

        self.models["teacher"] = tf.keras.models.load_model(
            teacher_path, custom_objects=CUSTOM_OBJECTS, compile=False
        )
        if TEACHER_DETERMINISTIC:  # before tracing, so the compiled function sees rate 0
            for layer in self.models["teacher"].layers:
                if isinstance(layer, tf.keras.layers.Dropout):  # incl. SpatialDropout1D
                    layer.rate = 0.0
        self.models["student"] = tf.keras.models.load_model(student_path, compile=False)
        self.paths = {"teacher": Path(teacher_path), "student": Path(student_path)}
        # A traced tf.function avoids eager-mode Python overhead (~30-100x faster on CPU).
        self._compiled = {
            name: tf.function(
                lambda x, m=model: m(x, training=False),
                input_signature=[tf.TensorSpec([None, WINDOW, 3], tf.float32)],
            )
            for name, model in self.models.items()
        }
        for name in self.models:
            for n in WARMUP_BATCH_SIZES:  # first calls trace/optimise; keep them out of timings
                self._run(name, np.zeros((n, WINDOW, 3), np.float32))
        self._ready = True  # only after warm-up, so no request ever sees half-loaded models

    def predict(self, name: str, windows: np.ndarray) -> ModelOutput:
        self._wait_for_load()
        return self._run(name, windows)

    def _run(self, name: str, windows: np.ndarray) -> ModelOutput:
        x = reorder(windows.astype(np.float32), CHANNEL_ORDER[name])
        with _INFERENCE_LOCK:
            start = time.perf_counter()
            outputs = self._compiled[name](x)
            detection, p, s = (o.numpy()[..., 0] for o in outputs)
            elapsed_ms = (time.perf_counter() - start) * 1000
        return ModelOutput(detection, p, s, latency_ms=elapsed_ms / len(windows))

    def info(self) -> dict:
        self._wait_for_load()
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
