"""Second coordinator for the optional private-cloud ("pro") API.

The official OAuth API exposes no blade/chassis service life, schedule or
settings. When the user also provides their Navimow app login (see the
config flow's pro_auth step), this coordinator polls the private cloud via the
vendored ``pro_api`` client for that extra, slow-changing data and exposes it
on the same mower device.

It is fully optional and defensive: any failure here is surfaced as a normal
coordinator update error and never affects the OAuth/MQTT primary path.

The maintenance parsing mirrors ilguala/navimow_pro (MIT); see pro_api/LICENSE.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_PRO_REGION, DOMAIN, PRO_API_DATA, PRO_UPDATE_INTERVAL
from .pro_api import (
    NavimowAuthError,
    NavimowCloudClient,
    NavimowError,
    PassportError,
    Tokens,
)

_LOGGER = logging.getLogger(__name__)


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    f = _as_float(value)
    return int(f) if f is not None else None


def _parse_maintenance(maintenance: Any) -> dict[str, Any]:
    """Blades/chassis life from get-component-maintenance.

    The endpoint returns ``{knife:{setTime,usedTime}, chassis:{...}, ...}`` where
    ``setTime`` is the reminder interval in HOURS and ``usedTime`` the component
    runtime in MINUTES, so life% = clamp(100*(1 - usedTime/(setTime*60)), 0, 100).
    """
    result: dict[str, Any] = {
        "blades_pct": None,
        "blades_set_hours": None,
        "blades_used_min": None,
        "chassis_pct": None,
        "chassis_set_hours": None,
        "chassis_used_min": None,
    }
    if not isinstance(maintenance, dict):
        return result

    def life(component: Any) -> tuple[int | None, int | None, int | None]:
        if not isinstance(component, dict):
            return None, None, None
        set_hours = _as_float(component.get("setTime"))
        used_min = _as_float(component.get("usedTime"))
        pct = None
        if set_hours is not None and used_min is not None and set_hours > 0:
            pct = 100.0 * (1.0 - used_min / (set_hours * 60.0))
            pct = round(max(0.0, min(100.0, pct)))
        return pct, _as_int(set_hours), _as_int(used_min)

    result["blades_pct"], result["blades_set_hours"], result["blades_used_min"] = life(
        maintenance.get("knife")
    )
    (
        result["chassis_pct"],
        result["chassis_set_hours"],
        result["chassis_used_min"],
    ) = life(maintenance.get("chassis"))
    return result


class NavimowProCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls the private-cloud API for extra per-device data, keyed by serial."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_pro",
            update_interval=timedelta(seconds=PRO_UPDATE_INTERVAL),
        )
        self.config_entry = config_entry
        pro = dict(config_entry.data.get(PRO_API_DATA) or {})
        region = pro.get(CONF_PRO_REGION) or "fra"
        self._client = NavimowCloudClient(
            device_id=pro.get("device_id") or "",
            tokens=Tokens(
                access_token=pro.get("access_token", ""),
                refresh_token=pro.get("refresh_token", ""),
                uuid=pro.get("uuid", ""),
                region=pro.get(CONF_PRO_REGION, "") or region,
            ),
            uid=pro.get("uid", ""),
            region=region,
            host=pro.get("host") or None,
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            data, session = await self.hass.async_add_executor_job(self._fetch_blocking)
        except (NavimowAuthError, NavimowError, PassportError, OSError) as err:
            # Kept isolated: a bad app session only makes the pro sensors
            # unavailable; it never triggers reauth of the OAuth entry.
            raise UpdateFailed(f"Private-cloud update failed: {err}") from err
        # Persist refreshed tokens/uid on the event loop so they survive restarts.
        self._persist_session(session)
        return data

    def _fetch_blocking(self) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        """Runs in an executor thread: ensure session, then read per-vehicle data."""
        self._ensure_session()
        try:
            vehicles = self._client.auth_list()
        except NavimowAuthError:
            self._client.refresh_session()
            self._client.mower_login()
            vehicles = self._client.auth_list()

        data: dict[str, dict[str, Any]] = {}
        for vehicle in vehicles:
            if not isinstance(vehicle, dict):
                continue
            sn = str(vehicle.get("vehicle_sn") or "")
            if not sn:
                continue
            try:
                maintenance = _parse_maintenance(self._client.maintenance(sn))
            except NavimowError as err:
                _LOGGER.debug("maintenance fetch failed for %s: %s", sn, err)
                maintenance = _parse_maintenance(None)
            data[sn] = {"maintenance": maintenance}
        return data, self._client.session_state()

    def _ensure_session(self) -> None:
        """Make sure we have a uid, refreshing the token once if needed."""
        if self._client.uid:
            return
        try:
            self._client.mower_login()
        except NavimowAuthError:
            self._client.refresh_session()
            self._client.mower_login()

    def _persist_session(self, session: dict[str, str]) -> None:
        """Write refreshed session fields back into the config entry (on loop)."""
        current = dict(self.config_entry.data.get(PRO_API_DATA) or {})
        updated = {
            **current,
            "access_token": session.get("access_token", current.get("access_token", "")),
            "refresh_token": session.get(
                "refresh_token", current.get("refresh_token", "")
            ),
            "uuid": self._client.tokens.uuid or current.get("uuid", ""),
            "uid": session.get("uid", current.get("uid", "")),
            CONF_PRO_REGION: session.get("region", current.get(CONF_PRO_REGION, "")),
            "device_id": self._client.device_id or current.get("device_id", ""),
            "host": session.get("host", current.get("host", "")),
        }
        if updated == current:
            return
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, PRO_API_DATA: updated},
        )

    def maintenance_for(self, serial: str) -> dict[str, Any]:
        """Parsed maintenance dict for a device serial (empty if unavailable)."""
        if not self.data:
            return {}
        return (self.data.get(serial) or {}).get("maintenance") or {}
