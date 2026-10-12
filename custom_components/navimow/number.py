"""Number platform for Navimow: controllable numeric private-cloud settings.

Battery thresholds (return-to-dock level, charging limit). Writing a value
takes two calls like the switches: a device command (``s:mower``) that encodes
the value as a two-digit hex string, and a cloud persist (``save_setting_iot``)
that uses a bare decimal. Encoding mirrors ilguala/navimow_pro (MIT).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .pro_coordinator import NavimowProCoordinator


@dataclass(frozen=True, kw_only=True)
class NavimowNumberEntityDescription(NumberEntityDescription):
    """A numeric mower setting (same key on both write channels)."""

    setting_key: str
    write_key: str


NUMBERS: tuple[NavimowNumberEntityDescription, ...] = (
    NavimowNumberEntityDescription(
        key="return_battery_level",
        translation_key="return_battery_level",
        icon="mdi:battery-arrow-down",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=5,
        native_max_value=50,
        native_step=5,
        mode=NumberMode.SLIDER,
        setting_key="return_battery_level",
        write_key="returnBatteryLevel",
    ),
    NavimowNumberEntityDescription(
        key="charging_limit",
        translation_key="charging_limit",
        icon="mdi:battery-charging-high",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=50,
        native_max_value=100,
        native_step=5,
        mode=NumberMode.SLIDER,
        setting_key="charging_limit",
        write_key="chargingLimit",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Navimow number settings (only with the optional app login)."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    pro_coordinator = data.get("pro_coordinator")
    if pro_coordinator is None:
        return

    entities: list[NavimowSettingNumber] = []
    for device in data["devices"]:
        settings = pro_coordinator.settings_for(device.id)
        for description in NUMBERS:
            if settings.get(description.setting_key) is not None:
                entities.append(
                    NavimowSettingNumber(pro_coordinator, device, description)
                )
    async_add_entities(entities)


class NavimowSettingNumber(
    CoordinatorEntity[NavimowProCoordinator], NumberEntity
):
    """A controllable numeric mower setting via the private cloud."""

    entity_description: NavimowNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NavimowProCoordinator,
        device: Any,
        entity_description: NavimowNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._serial = device.id
        self._optimistic: int | None = None
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
    def native_value(self) -> float | None:
        if self._optimistic is not None:
            return float(self._optimistic)
        value = self.coordinator.settings_for(self._serial).get(
            self.entity_description.setting_key
        )
        return None if value is None else float(value)

    def _handle_coordinator_update(self) -> None:
        self._optimistic = None
        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        desc = self.entity_description
        client = self.coordinator.client
        wire = int(round(value))
        # 1) device command (hex string) so the robot applies it.
        await self.coordinator.async_send(
            client.send_setting_device, self._serial, {desc.write_key: f"{wire:02X}"}
        )
        # 2) cloud persist (iot_set), bare decimal for the percentages.
        await self.coordinator.async_send(
            client.save_setting_iot,
            self._serial,
            self.coordinator.vehicle_type_for(self._serial),
            {desc.write_key: wire},
        )
        self._optimistic = wire
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
