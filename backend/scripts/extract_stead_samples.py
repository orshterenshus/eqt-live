"""Save 5 held-out STEAD earthquake traces with catalog P/S picks as a test fixture.

Run with the project's `eqt` conda env (SeisBench + STEAD cache on E:):
  <eqt python> scripts/extract_stead_samples.py tests/fixtures/stead_samples.npz
Uses the same seeded permutation as EQ_Project training; order[510000:] never
overlaps the training set.
"""
import sys

import numpy as np
import seisbench.data as sbd

out = sys.argv[1]
ds = sbd.STEAD(component_order="ZNE")  # the SeisBench default used in training
meta = ds.metadata
order = np.random.default_rng(42).permutation(len(ds))
chosen = []
for idx in order[510000:]:
    row = meta.iloc[int(idx)]
    if row["trace_category"] != "earthquake_local":
        continue
    if np.isnan(row["trace_p_arrival_sample"]) or np.isnan(row["trace_s_arrival_sample"]):
        continue
    chosen.append(int(idx))
    if len(chosen) == 5:
        break

waves = np.stack([ds.get_waveforms(i) for i in chosen]).astype(np.float32)
p = meta.iloc[chosen]["trace_p_arrival_sample"].to_numpy(dtype=float)
s = meta.iloc[chosen]["trace_s_arrival_sample"].to_numpy(dtype=float)
assert waves.shape == (5, 3, 6000), waves.shape
np.savez_compressed(out, waves=waves, p=p, s=s)
print(f"Saved {out}: indices={chosen} p={p} s={s}")
