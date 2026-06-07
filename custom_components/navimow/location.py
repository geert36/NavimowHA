"""Real-time location and zone decoding for Navimow."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def location_topic(device_id: str) -> str:
    """Return the MQTT topic that carries live mower pose and zone data."""
    return f"/downlink/vehicle/{device_id}/realtimeDate/location"


def position_topic(device_id: str) -> str:
    """Return the MQTT topic that carries live mower position data."""
    return f"/downlink/vehicle/{device_id}/realtimeDate/position"


def parse_location_payload(
    cache: dict[str, dict[str, Any]], device_id: str, data: Any
) -> dict[str, Any] | None:
    """Merge one location message into the per-device cache."""
    if not isinstance(data, list):
        return None

    location = dict(cache.get(device_id) or {})
    location["device_id"] = device_id
    location["raw_payload"] = data
    location["payload_types"] = [
        item.get("type") for item in data if isinstance(item, dict) and "type" in item
    ]
    changed = False
    unknown_items: list[dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        payload_type = item.get("type")
        if payload_type == 1:
            try:
                location["x"] = float(item["postureX"])
                location["y"] = float(item["postureY"])
                location["theta"] = float(item["postureTheta"])
            except (KeyError, TypeError, ValueError):
                pass
            if "vehicleState" in item:
                location["vehicle_state"] = item["vehicleState"]
            if "time" in item:
                location["pose_time"] = item["time"]
                location["pose_time_iso"] = _format_unix_milliseconds(item["time"])
            changed = True
        elif payload_type == 2:
            if "action" in item:
                location["mow_action"] = item["action"]
            if "currentMowBoundary" in item:
                location["current_mow_boundary"] = item["currentMowBoundary"]
            if "currentMowProgress" in item:
                location["current_mow_progress"] = _coerce_number(
                    item["currentMowProgress"]
                )
            if "mapWorkPosition" in item:
                location["map_work_position"] = item["mapWorkPosition"]
            if "mowStartType" in item:
                location["mow_start_type"] = item["mowStartType"]
            if "mowingPercentage" in item:
                location["mowing_percentage"] = _coerce_number(
                    item["mowingPercentage"]
                )
            if "mowingWeekArea" in item:
                location["mowing_week_area"] = _coerce_number(item["mowingWeekArea"])
            if "subtotalArea" in item:
                location["subtotal_area"] = _coerce_number(item["subtotalArea"])
            if "time" in item:
                location["mow_progress_time"] = item["time"]
                location["mow_progress_time_iso"] = _format_unix_milliseconds(
                    item["time"]
                )
            changed = True
        elif payload_type == 3:
            partition_ids = item.get("partitionIds")
            location["partition_ids"] = partition_ids
            location["partition"] = (
                partition_ids[0]
                if isinstance(partition_ids, list) and partition_ids
                else None
            )
            changed = True
        elif payload_type == 4:
            location["task_delay"] = item.get("taskDelay")
            changed = True
        else:
            unknown_items.append(item)
            changed = True

    if unknown_items:
        location["unknown_items"] = unknown_items
    else:
        location.pop("unknown_items", None)

    if not changed:
        return None

    cache[device_id] = location
    return location


def _coerce_number(value: Any) -> int | float | str | None:
    """Convert numeric-looking values while preserving unknown payloads."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return int(number)
    return number


def _format_unix_milliseconds(value: Any) -> str | None:
    """Convert a Unix timestamp in milliseconds into an ISO UTC string."""
    try:
        milliseconds = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc).isoformat()
