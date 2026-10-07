"""Pydantic response models (they also generate the OpenAPI docs at /docs)."""
from datetime import datetime

from pydantic import BaseModel


class EventOut(BaseModel):
    id: str
    time: datetime
    magnitude: float
    lat: float
    lon: float
    depth_km: float
    place: str


class StationOut(BaseModel):
    id: str
    network: str
    station: str
    location: str
    band: str
    lat: float
    lon: float
    distance_km: float


class LiveStationOut(BaseModel):
    id: str
    label: str


class Curves(BaseModel):
    detection: list[float]
    p: list[float]
    s: list[float]


class ModelResult(BaseModel):
    detected: bool
    detection_max: float
    p_time: datetime | None
    s_time: datetime | None
    p_conf: float | None
    s_conf: float | None
    latency_ms: float
    curves: Curves


class Waveform(BaseModel):
    z: list[float]
    n: list[float]
    e: list[float]


class Theoretical(BaseModel):
    p_time: datetime | None
    s_time: datetime | None


class AnalysisResult(BaseModel):
    station: str
    distance_km: float | None
    start_time: datetime
    display_dt: float  # seconds between displayed points
    waveform: Waveform
    theoretical: Theoretical
    teacher: ModelResult
    student: ModelResult


class ModelInfo(BaseModel):
    name: str
    params: int
    size_mb: float


class ModelsOut(BaseModel):
    teacher: ModelInfo
    student: ModelInfo
    compression: float


class HealthOut(BaseModel):
    status: str
    models_loaded: bool
