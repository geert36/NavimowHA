"""Binary sensor platform for Navimow (optional private-cloud settings)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .pro_coordinator import NavimowProCoordinator


@dataclass(frozen=True, kw_only=True)
class NavimowProBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a binary sensor fed by the private-cloud settings."""

    # Key into the pro coordinator's per-device settings dict.
    setting_key: str


# Read-only mower settings surfaced as individual binary sensors. The full set
# stays available as attributes on the diagnostic "Settings" sensor.
PRO_BINARY_SENSOR_DESCRIPTIONS: tuple[
    NavimowProBinarySensorEntityDescription, ...
] = (
    NavimowProBinarySensorEntityDescription(
        key="schedule_enabled",
        translation_key="schedule_enabled",
        setting_key="schedule_enabled",
        icon="mdi:calendar-check",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NavimowProBinarySensorEntityDescription(
        key="night_mow",
        translation_key="night_mow",
        setting_key="night_mow",
        icon="mdi:weather-night",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NavimowProBinarySensorEntityDescription(
        key="rain_sensor",
        translation_key="rain_sensor",
        setting_key="rain_sensor",
        icon="mdi:weather-rainy",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NavimowProBinarySensorEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        setting_key="child_lock",
        icon="mdi:lock",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NavimowProBinarySensorEntityDescription(
        key="lift_alarm",
        translation_key="lift_alarm",
        setting_key="lift_alarm",
        icon="mdi:arrow-up-bold-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NavimowProBinarySensorEntityDescription(
        key="obstacle_avoid",
        translation_key="obstacle_avoid",
        setting_key="obstacle_avoid",
        icon="mdi:wall",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Navimow binary sensors (only with the optional app login)."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    pro_coordinator = data.get("pro_coordinator")
    if pro_coordinator is None:
        return

    entities: list[NavimowProBinarySensor] = []
    for device in data["devices"]:
        for description in PRO_BINARY_SENSOR_DESCRIPTIONS:
            entities.append(
                NavimowProBinarySensor(pro_coordinator, device, description)
            )
    async_add_entities(entities)


class NavimowProBinarySensor(
    CoordinatorEntity[NavimowProCoordinator], BinarySensorEntity
):
    """A mower setting exposed as a binary sensor via the private cloud."""

    entity_description: NavimowProBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NavimowProCoordinator,
        device: Any,
        entity_description: NavimowProBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._serial = device.id
        self._attr_unique_id = f"{DOMAIN}_{device.id}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer="Navimow",
            model=device.model or "Unknown",
            sw_version=device.firmware_version or None,
            serial_number=device.serial_number or device.id,
        )

    @property
    def is_on(self) -> bool | None:
        """Return the setting's boolean value (None if unavailable)."""
        settings = self.coordinator.settings_for(self._serial)
        return settings.get(self.entity_description.setting_key)
