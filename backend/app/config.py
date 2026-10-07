"""Project-wide constants and paths."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/ (or /app in Docker)
MODELS_DIR = BASE_DIR / "models"
TEACHER_PATH = MODELS_DIR / "teacher.h5"
STUDENT_PATH = MODELS_DIR / "student.h5"
STATIC_DIR = Path(os.environ.get("EQT_STATIC_DIR", BASE_DIR.parent / "frontend" / "dist"))

# Model I/O
SAMPLING_RATE = 100.0
WINDOW = 6000
STRIDE = 3000
DETECTION_THRESHOLD = 0.5
PICK_THRESHOLD = 0.3
DISPLAY_POINTS = 3000

# External services
USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
FDSN_PROVIDER = "IRIS"
HTTP_TIMEOUT = 10
STATION_RADIUS_DEG = 3.0
MAX_STATIONS = 10
PRE_P_SECONDS = 30
POST_P_SECONDS = 90
LIVE_SECONDS = 120
LIVE_DELAY_SECONDS = 300
CACHE_TTL_SECONDS = 1800

LIVE_STATIONS = [
    ("IU.ANMO.00.BH", "IU.ANMO – Albuquerque, New Mexico, USA"),
    ("II.PFO.00.BH", "II.PFO – Pinon Flat, California, USA"),
    ("IU.COLA.00.BH", "IU.COLA – College, Alaska, USA"),
    ("IU.HRV.00.BH", "IU.HRV – Harvard, Massachusetts, USA"),
    ("IU.MAJO.00.BH", "IU.MAJO – Matsushiro, Japan"),
    ("IU.TATO.00.BH", "IU.TATO – Taipei, Taiwan"),
    ("IU.SNZO.00.BH", "IU.SNZO – Wellington, New Zealand"),
    ("IU.KONO.00.BH", "IU.KONO – Kongsberg, Norway"),
]
