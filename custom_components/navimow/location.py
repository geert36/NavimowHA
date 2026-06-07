"""Real-time location and zone decoding for Navimow."""
from __future__ import annotations

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
