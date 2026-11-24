"""Firmware version decoding for Navimow.

The cloud sends each firmware module's version as four characters, such as
``0066``. The app shows that as ``1.`` followed by the last three characters,
dot-separated: ``0066`` reads ``1.0.6.6``. The same wire format comes back from
the official ``authList`` (as ``firmware``, the ACU module) and from the
private ``get-firmware-list`` endpoint (one entry per module). Decoding mirrors
ilguala/navimow_pro (MIT).
"""
from __future__ import annotations

import re
from typing import Any

_FIRMWARE_WIRE = re.compile(r"0[0-9A-Fa-f]{3}")

# Module type on the wire -> key used for the sensor. The comments give the
# label the app's Software-update screen uses for that module.
FIRMWARE_MODULES: dict[str, str] = {
    "sw": "firmware_acu",  # ACU-firmware (the main firmware)
    "ecu": "firmware_ecu",  # ECU-firmware
    "vcu": "firmware_vcu",  # Firmware voertuigbesturing
    "cgs": "firmware_charging_station",  # Laadstation-firmware
    "swdp": "firmware_vision_core",  # Firmware Vision core
}


def format_firmware(wire: Any) -> str | None:
    """Return a module version as the app writes it (``0066`` -> ``1.0.6.6``).

    Only the four-character wire shape is rewritten; any other value is
    returned as it came, so an unexpected format is never mangled.
    """
    if wire is None:
        return None
    text = str(wire).strip()
    if not text:
        return None
    if _FIRMWARE_WIRE.fullmatch(text):
        return "1." + ".".join(text[1:])
    return text


def parse_firmware(payload: Any) -> dict[str, Any]:
    """Pull the module versions and the OS version out of get-firmware-list.

    Returns ``{"modules": {key: "1.0.6.6", ...}, "os": "4.3.5",
    "os_latest": "4.3.5"}``; missing parts are left out.
    """
    if not isinstance(payload, dict):
        return {}
    out: dict[str, Any] = {}
    modules: dict[str, str] = {}
    for item in payload.get("firmwareList") or []:
        if not isinstance(item, dict):
            continue
        key = FIRMWARE_MODULES.get(str(item.get("type") or "").lower())
        version = format_firmware(item.get("version"))
        if key and version:
            modules[key] = version
    if modules:
        out["modules"] = modules
    os_info = payload.get("osInfo")
    if isinstance(os_info, dict):
        current = os_info.get("currentVersion")
        latest = os_info.get("newVersion")
        if current:
            out["os"] = str(current)
        if latest:
            out["os_latest"] = str(latest)
    return out
