"""Recent earthquakes from the USGS FDSN event service."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.config import HTTP_TIMEOUT, USGS_URL
from app.errors import NotFoundError, UpstreamError


@dataclass
class Event:
    id: str
    time: datetime
    magnitude: float
    lat: float
    lon: float
    depth_km: float
    place: str


def parse_feature(feature: dict) -> Event:
    props = feature["properties"]
    lon, lat, depth = feature["geometry"]["coordinates"][:3]
    return Event(
        id=feature["id"],
        time=datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc),
        magnitude=float(props["mag"]),
        lat=float(lat),
        lon=float(lon),
        depth_km=float(depth),
        place=props.get("place") or "Unknown location",
    )


def parse_feed(data: dict) -> list[Event]:
    return [parse_feature(f) for f in data["features"] if f["properties"].get("mag") is not None]


def _get(params: dict) -> dict:
    last_error: Exception | None = None
    for _ in range(2):  # one retry
        try:
            response = httpx.get(USGS_URL, params=params, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 404):
                raise NotFoundError("Earthquake not found in the USGS catalog") from e
            last_error = e
        except httpx.HTTPError as e:
            last_error = e
    raise UpstreamError("USGS earthquake service unavailable") from last_error


def fetch_recent(days: int = 3, min_mag: float = 4.0, limit: int = 100) -> list[Event]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    data = _get({
        "format": "geojson",
        "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": min_mag,
        "orderby": "time",
        "limit": limit,
    })
    return parse_feed(data)


def fetch_event(event_id: str) -> Event:
    return parse_feature(_get({"format": "geojson", "eventid": event_id}))
