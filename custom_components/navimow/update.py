"""Update platform for Navimow: shows when a newer Navimow OS is available.

Read-only: the private cloud's get-firmware-list reports the installed and the
newest Navimow OS version, so this entity shows "update available" when the
two differ. Installing is left to the Navimow app; nothing here starts an
update. Only created when the optional app login is set up and the mower
reports its OS version.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .pro_coordinator import NavimowProCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Navimow OS update entity (only with the optional app login)."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    pro_coordinator = data.get("pro_coordinator")
    if pro_coordinator is None:
        return

    async_add_entities(
        NavimowOSUpdate(pro_coordinator, device)
        for device in data["devices"]
        if pro_coordinator.firmware_for(device.id).get("os")
    )


class NavimowOSUpdate(CoordinatorEntity[NavimowProCoordinator], UpdateEntity):
    """Installed vs. newest Navimow OS, as the app's Software-update screen."""

    _attr_has_entity_name = True
    _attr_translation_key = "navimow_os"
    _attr_title = "Navimow OS"

    def __init__(self, coordinator: NavimowProCoordinator, device: Any) -> None:
        super().__init__(coordinator)
        self._serial = device.id
        self._attr_unique_id = f"{DOMAIN}_{device.id}_navimow_os_update"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer="Navimow",
            model=device.model or "Unknown",
            sw_version=device.firmware_version or None,
            serial_number=device.serial_number or device.id,
        )

    @property
    def installed_version(self) -> str | None:
        return self.coordinator.firmware_for(self._serial).get("os")

    @property
    def latest_version(self) -> str | None:
        firmware = self.coordinator.firmware_for(self._serial)
        return firmware.get("os_latest") or firmware.get("os")
