"""FastAPI application: JSON API under /api plus the built frontend at /."""
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Path, Query, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import events, service
from app.cache import ResultCache
from app.config import LIVE_STATIONS, STATIC_DIR
from app.errors import AppError
from app.models import ModelRunner
from app.schemas import (
    AnalysisResult, EventOut, HealthOut, LiveStationOut, ModelsOut, StationOut,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("eqt_live")
EVENT_ID_MAX = 40


def create_app(runner=None, load_models: bool = True) -> FastAPI:
    runner = runner or ModelRunner()
    cache = ResultCache()
    live_cache = ResultCache(ttl=120, maxsize=16)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if load_models and not runner.loaded:
            try:
                runner.load()
                log.info("Models loaded")
            except Exception:
                log.exception("Model loading failed")
        yield

    app = FastAPI(title="EQT-Live", version="1.0.0", lifespan=lifespan)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code,
                            content={"error": exc.code, "message": exc.message})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        parts = [f"{'.'.join(str(x) for x in e['loc'][1:]) or e['loc'][0]}: {e['msg']}"
                 for e in exc.errors()]
        return JSONResponse(status_code=422,
                            content={"error": "invalid_request", "message": "; ".join(parts)})

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if not request.url.path.startswith("/api"):
            return await http_exception_handler(request, exc)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "not_found" if exc.status_code == 404 else "http_error",
                     "message": str(exc.detail)},
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        log.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500,
                            content={"error": "internal_error",
                                     "message": "Internal server error"})

    @app.get("/health", response_model=HealthOut)
    def health():
        return HealthOut(status="ok", models_loaded=runner.loaded)

    @app.get("/api/events", response_model=list[EventOut])
    def get_events(days: int = Query(3, ge=1, le=7), min_mag: float = Query(4.0, ge=0, le=10)):
        return [EventOut(**asdict(e)) for e in events.fetch_recent(days=days, min_mag=min_mag)]

    @app.get("/api/events/{event_id}/stations", response_model=list[StationOut])
    def get_stations(event_id: str = Path(max_length=EVENT_ID_MAX)):
        return cache.get_or_compute(
            ("stations", event_id),
            lambda: [StationOut(id=s.id, **asdict(s)) for s in service.list_stations(event_id)],
        )

    @app.get("/api/analyze", response_model=AnalysisResult)
    def analyze(event_id: str = Query(max_length=EVENT_ID_MAX), station: str = Query(max_length=40)):
        return cache.get_or_compute(
            ("event", event_id, station),
            lambda: service.analyze_event(runner, event_id, station),
        )

    @app.get("/api/live/stations", response_model=list[LiveStationOut])
    def live_stations():
        return [LiveStationOut(id=sid, label=label) for sid, label in LIVE_STATIONS]

    @app.get("/api/live", response_model=AnalysisResult)
    def live(station: str):
        return service.analyze_live(runner, station, live_cache)

    @app.get("/api/models", response_model=ModelsOut)
    def models_info():
        return runner.info()

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
