"""Position helpers for Navimow payloads."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

LATITUDE_KEYS = (
    "lat",
    "latitude",
    "latGcj02",
    "latWgs84",
    "wgs84Lat",
    "gcj02Lat",
    "latitudeValue",
)
LONGITUDE_KEYS = (
    "lng",
    "lon",
    "longitude",
    "lngGcj02",
    "lngWgs84",
    "wgs84Lng",
    "gcj02Lng",
    "longitudeValue",
)
POSITION_KEYS = (
    "position",
    "location",
    "gps",
    "coordinate",
    "coordinates",
    "point",
    "pos",
)


def extract_position(position: Any) -> tuple[float | None, float | None]:
    """Extract latitude/longitude from known Navimow payload shapes."""
    payload = _to_plain(position)
    latitude, longitude = _extract_from_payload(payload, depth=0)
    if latitude is None or longitude is None:
        return None, None
    if -90 <= latitude <= 90 and -180 <= longitude <= 180:
        return latitude, longitude
    return None, None


def position_dict(position: Any) -> dict[str, float] | None:
    """Return a normalized position dict when coordinates are available."""
    latitude, longitude = extract_position(position)
    if latitude is None or longitude is None:
        return None
    return {"lat": latitude, "lng": longitude}


def _extract_from_payload(
    payload: Any, depth: int
) -> tuple[float | None, float | None]:
    if depth > 6:
        return None, None

    if isinstance(payload, dict):
        latitude = _first_float(payload, LATITUDE_KEYS)
        longitude = _first_float(payload, LONGITUDE_KEYS)
        if latitude is not None and longitude is not None:
            return latitude, longitude

        for key in POSITION_KEYS:
            if key in payload:
                latitude, longitude = _extract_from_payload(payload[key], depth + 1)
                if latitude is not None and longitude is not None:
                    return latitude, longitude

        for value in payload.values():
            if isinstance(value, (dict, list, tuple)):
                latitude, longitude = _extract_from_payload(value, depth + 1)
                if latitude is not None and longitude is not None:
                    return latitude, longitude
        return None, None

    if isinstance(payload, (list, tuple)):
        if len(payload) >= 2:
            first = _as_float(payload[0])
            second = _as_float(payload[1])
            if first is not None and second is not None:
                return first, second
        for value in payload:
            if isinstance(value, (dict, list, tuple)):
                latitude, longitude = _extract_from_payload(value, depth + 1)
                if latitude is not None and longitude is not None:
                    return latitude, longitude

    return None, None


def _first_float(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in payload:
            value = _as_float(payload[key])
            if value is not None:
                return value
    return None


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (dict, list, tuple)):
        return value
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except TypeError:
            pass
    if hasattr(value, "__dict__"):
        return vars(value)
    return value


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
