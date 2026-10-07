"""Compare both models with Z-N-E vs E-N-Z input on the STEAD fixture.

Usage (from backend/): python scripts/check_channel_order.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from app import models  # noqa: E402
from app.preprocess import standardize  # noqa: E402

d = np.load("tests/fixtures/stead_samples.npz")
windows = np.stack([standardize(w).T for w in d["waves"]])
runner = models.ModelRunner()
runner.load()
for name in ("teacher", "student"):
    for order in ("ZNE", "ENZ"):
        models.CHANNEL_ORDER[name] = order
        out = runner.predict(name, windows)
        p_ms = np.abs(out.p.argmax(axis=1) - d["p"]).mean() * 10
        s_ms = np.abs(out.s.argmax(axis=1) - d["s"]).mean() * 10
        det = out.detection.max(axis=1).mean()
        print(f"{name:8s} {order}: P error {p_ms:8.1f} ms | S error {s_ms:8.1f} ms | det {det:.2f}")
