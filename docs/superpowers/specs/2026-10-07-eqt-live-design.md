# EQT-Live — Design

**Date:** 2026-10-07
**Author:** Or Shterenshus
**Status:** Approved design, pending implementation plan

## 1. Goal

A public web service that runs the compressed EQTransformer **student** model (60,659 params,
from the final project *Compressing the Earthquake Transformer via Knowledge Distillation*) and the
original **teacher** model (373,495 params) side by side on **real seismic data**, showing
detections, P/S arrival picks and inference latency for both.

Purpose: a portfolio project for full-time Software Engineer applications. It must demonstrate
backend development, integration with external APIs, ML model serving, a typed frontend, testing,
Docker, CI/CD and cloud deployment, all reachable through a live link.

### Success criteria
- A visitor opens the live URL, clicks a recent earthquake, and within ~10 s sees the waveform,
  P/S picks from both models, theoretical arrivals and a latency comparison.
- CI runs lint, tests, type-check and a Docker build on every push. A push to `main` deploys
  automatically.
- The README lets a reviewer understand the project in under a minute.

### Non-goals (v1)
- Continuous streaming (SeedLink/WebSocket). This is a possible phase 2.
- User accounts, persistence or a database.
- GPU inference.
- UI polish beyond a clean, functional layout (planned as a later iteration).

## 2. Architecture

One Docker container, deployed as a **Hugging Face Space** (Docker SDK, port 7860).
FastAPI serves both the JSON API (`/api/*`) and the built React app (static files), so there is
one origin and no CORS configuration.

```
Browser ──► FastAPI
             ├── static React build (/)
             └── /api/*
                  ├── events.py     ──► USGS earthquake GeoJSON feed
                  ├── stations.py   ──► FDSN (EarthScope/IRIS) station + dataselect, via ObsPy
                  ├── preprocess.py     pure signal processing
                  ├── models.py         Teacher + Student inference (loaded once at startup)
                  ├── picks.py          probability curves → detection + P/S times
                  └── cache.py          in-memory TTL cache
```

### Backend modules

| Module | Responsibility | External dependency |
|---|---|---|
| `events.py` | Fetch and parse recent earthquakes (id, time, magnitude, lat, lon, depth, place) | USGS FDSN event / GeoJSON feed |
| `stations.py` | Find nearby 3-component stations for an event (sorted by distance, max 10); download the waveform window; compute theoretical P/S arrivals with `obspy.taup` (iasp91) | FDSN station + dataselect |
| `preprocess.py` | Merge gaps, require Z/N/E channels, resample to 100 Hz, slice into 6000-sample windows with 3000-sample stride, per-window per-channel z-score (mean 0, std 1; zero-std channels left at zero), order channels to match training | none |
| `models.py` | Load Teacher (`EqT_original_model.h5`, with vendored custom layers) and Student (`student_model.h5`) once; run batch inference; measure latency per window | TensorFlow-CPU 2.15 |
| `picks.py` | From the 3 output curves (detection, P, S): detection if max detection prob ≥ 0.5; P/S pick = argmax of curve if max ≥ 0.3; convert (window index, sample index) to absolute UTC time; across overlapping windows keep the highest-confidence pick; stitch curves into one timeline for display | none |
| `cache.py` | TTL cache (30 min) keyed by `(event_id, station)` / `(station, minute)` | none |
| `api.py` / `main.py` | Route definitions, Pydantic schemas, startup model loading, static file serving | FastAPI |

### Key technical decisions
- **TensorFlow-CPU 2.15**, the last release on Keras 2, which loads the legacy `.h5` files and
  EQTransformer custom layers. Keras 3 (TF ≥ 2.16) is avoided.
- **Vendored teacher layers.** Only `SeqSelfAttention`, `FeedForward` and `LayerNormalization`
  (plus the `f1` metric stub) are copied from `EQTransformer/core/EqT_utils.py` (MIT license),
  with attribution.
- **Preprocessing parity with training.** Mirrors `EQ_Project/kd_framework/data.py`: resample to
  6000 samples per 60 s window and per-channel standardization. No extra filtering is applied,
  since training applied none.
- **Channel order must be verified first.** SeisBench's default component order is `ZNE`, while
  the original EQTransformer expects `ENZ`. Task 1 of the plan establishes which order each model
  actually received in training (using a STEAD sample with known picks) and fixes it as a
  constant per model, covered by a test.
- **Models in git via Git LFS.** Student is 0.4 MB and Teacher is 5.1 MB. Hugging Face rejects
  binary files that are not tracked by LFS, so `*.h5`, `*.npz` and images are LFS-tracked from
  the first commit.
- **Stations within 3° (~330 km).** Both models were trained on STEAD, which consists of local
  events, so only nearby stations are offered. Events without nearby 3-component stations show
  "no nearby stations".

## 3. API

All responses are Pydantic models; OpenAPI docs at `/docs`.

| Endpoint | Returns |
|---|---|
| `GET /api/events?days=3&min_mag=4.5` | List of events: `id, time, magnitude, lat, lon, depth_km, place` |
| `GET /api/events/{event_id}/stations` | Up to 10 stations: `network, station, lat, lon, distance_km` |
| `GET /api/analyze?event_id=…&station=NET.STA` | Analysis result (below), window ≈ P_theoretical − 30 s to + 90 s |
| `GET /api/live?station=NET.STA` | Analysis result for the station's most recent ~2 minutes (no theoretical arrivals). The station must be in a curated list of ~8 reliable global stations |
| `GET /api/live/stations` | The curated live station list: `id, label` |
| `GET /api/models` | Static model facts: params, file size, compression ratio |
| `GET /health` | `{status, models_loaded}` |

**Analysis result:**
```
{
  station, distance_km?, start_time, sampling_rate_display,
  waveform: { z: [...], n: [...], e: [...] },          // downsampled to ~3000 pts/channel
  theoretical: { p_time?, s_time? },
  teacher: { detected, p_time?, s_time?, p_conf?, s_conf?,
             curves: { detection, p, s }, latency_ms },
  student: { …same shape… }
}
```

### Request flow for `/api/analyze`
1. Cache lookup.
2. Resolve event, compute distance and theoretical arrivals, download Z/N/E for the window.
3. Preprocess into `(n_windows, 6000, 3)`.
4. Run Teacher and Student on the same batch, timing each.
5. Extract picks, stitch curves, downsample the waveform for display.
6. Cache and return.

## 4. Error handling
- External calls (USGS, FDSN) use a 10 s timeout and one retry. On failure → **502** with a
  message naming the service.
- Unknown event or station → **404**. Invalid parameters → **422** (FastAPI validation).
- Missing channels or a too-short trace → **422** `insufficient_data`; the UI suggests another
  station.
- Model load failure at startup → `/health` reports `models_loaded: false` and analysis
  endpoints return **503**.
- One structured log line per analysis request: event, station, latencies, outcome.

## 5. Frontend

Vite + React + TypeScript; Leaflet (map), Plotly (`react-plotly.js`) for charts, TanStack Query
for data fetching. Single page, two tabs, no router.

- **Recent Earthquakes tab:** world map plus a list (magnitude filter) → select event → station
  dropdown → waveform chart (3 channels, vertical lines for Teacher / Student / theoretical P and
  S), probability-curve chart, and a comparison card (detected, P/S times and deltas, latency,
  speed-up, model size).
- **Live Station tab:** curated station dropdown, the same analysis view, auto-refresh every
  60 s, and a banner explaining that no detection is the normal case.
- **About panel:** knowledge distillation in brief, key research numbers, links to GitHub and
  LinkedIn.
- Loading states with step text; clear error messages for no-data and service-down cases.

```
src/api/client.ts            typed fetchers + types mirroring the API
src/components/              EventMap, EventList, StationPicker, WaveformChart,
                             ProbabilityChart, ComparisonCard, AboutPanel
src/tabs/                    RecentTab, LiveTab
src/App.tsx
```

## 6. Testing
Tests never call the network: USGS and FDSN responses are recorded once as fixtures and
replayed.

- `preprocess`: output shape, per-channel mean≈0 / std≈1, resampling 40 → 100 Hz, missing-channel
  error, zero-std channel.
- `picks`: known peak → exact time; below threshold → no pick; overlap merging keeps the higher
  confidence.
- `models`: both models load; on a saved STEAD sample with known picks, the Student's P pick is
  within 0.5 s; channel-order test.
- `events` / `stations`: fixture parsing; timeout → clean exception.
- API: `TestClient` with external calls mocked, checking status codes and response schema.
- Frontend: Vitest + React Testing Library for ComparisonCard rendering and the error state.

## 7. CI/CD & deployment
GitHub Actions:
- **On push / PR:** backend (`ruff`, `pytest`), frontend (`npm ci`, `tsc --noEmit`, `vitest`,
  `vite build`), Docker image build.
- **On push to `main` after all jobs pass:** push to the Hugging Face Space git remote using an
  `HF_TOKEN` GitHub secret (created by the owner, never handled by tooling).

Multi-stage Dockerfile: `node:20` builds the frontend, then `python:3.11-slim` installs the backend
deps, copies the code, models and static build, and runs `uvicorn` on port 7860. A
`docker-compose.yml` is provided for local runs.

## 8. Repository deliverables
README with live link, screenshot/GIF, architecture diagram, short "how it works", local run
instructions, CI badge, link to the research; MIT license; attribution to EQTransformer
(Mousavi et al., 2020).

## 9. Build order
1. Verify channel order; implement `preprocess`, `models`, `picks` with tests (offline core).
2. `events` and `stations` (USGS / FDSN) with fixtures.
3. FastAPI endpoints, cache, error handling, API tests.
4. Frontend (functional first, polish later).
5. Dockerfile, CI, Hugging Face deployment.
6. README; add the project to the CV.
