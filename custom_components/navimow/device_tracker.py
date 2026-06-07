"""Device tracker platform for Navimow integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NavimowCoordinator
from .position import extract_position


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Navimow device tracker entities from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    devices = data["devices"]
    coordinators: dict[str, NavimowCoordinator] = data["coordinators"]

    async_add_entities(
        NavimowDeviceTracker(coordinator=coordinators[device.id])
        for device in devices
    )


class NavimowDeviceTracker(CoordinatorEntity[NavimowCoordinator], TrackerEntity):
    """Navimow mower location entity."""

    _attr_has_entity_name = True
    _attr_name = "Location"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: NavimowCoordinator) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        device = coordinator.device
        self._attr_unique_id = f"{DOMAIN}_{device.id}_location"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer="Navimow",
            model=device.model or "Unknown",
            sw_version=device.firmware_version or None,
            serial_number=device.serial_number or device.id,
        )

    @property
    def available(self) -> bool:
        """Return true when a cached state exists."""
        return self.coordinator.get_device_state() is not None or super().available

    @property
    def latitude(self) -> float | None:
        """Return latitude."""
        state = self.coordinator.get_device_state()
        if not state:
            return None
        latitude, _longitude = extract_position(state.position)
        return latitude

    @property
    def longitude(self) -> float | None:
        """Return longitude."""
        state = self.coordinator.get_device_state()
        if not state:
            return None
        _latitude, longitude = extract_position(state.position)
        return longitude

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return raw position payload for diagnostics."""
        state = self.coordinator.get_device_state()
        if not state or not state.position:
            return {}
        return {"position": state.position}
