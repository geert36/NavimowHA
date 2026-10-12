"""Switch platform for Navimow: controllable private-cloud settings.

Writing a setting takes two calls, mirroring the app (and ilguala/navimow_pro,
MIT): a device command (``send_setting_device``, ``s:mower``) so the robot
actually applies the change, and a cloud persist (``set_iot_bool`` with
``iot_set`` for "modern" keys, or the plain ``set_bool_setting`` for legacy
keys). The per-key value encoding differs between the two channels, so each
switch description carries both. Only created when the optional app login is
set up and the robot reports the key.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .pro_coordinator import NavimowProCoordinator


@dataclass(frozen=True, kw_only=True)
class NavimowSwitchEntityDescription(SwitchEntityDescription):
    """A boolean mower setting mapped to its two write encodings."""

    setting_key: str
    write_key: str
    # "modern" setting: cloud write via save-set-data + iot_set, plus a device
    # command. Legacy (iot=False) uses the plain set_bool_setting only.
    iot: bool = False
    # Cloud iot value encoding: True => JSON number 1/0, False => string "1"/"0".
    numeric: bool = False
    # Device-command value encoding: True => JSON number 1/0, False => "1"/"0".
    robot_numeric: bool = True


SWITCHES: tuple[NavimowSwitchEntityDescription, ...] = (
    NavimowSwitchEntityDescription(
        key="schedule_enabled",
        translation_key="schedule_enabled",
        icon="mdi:calendar-check",
        entity_category=EntityCategory.CONFIG,
        setting_key="schedule_enabled",
        write_key="startPlan",
        iot=True,
        numeric=False,  # cloud string "1"/"0"
        robot_numeric=False,  # robot string "1"/"0"
    ),
    NavimowSwitchEntityDescription(
        key="night_mow",
        translation_key="night_mow",
        icon="mdi:weather-night",
        entity_category=EntityCategory.CONFIG,
        setting_key="night_mow",
        write_key="nightMowSwitch",
        iot=True,
        numeric=True,  # cloud number 1/0
    ),
    NavimowSwitchEntityDescription(
        key="rain_sensor",
        translation_key="rain_sensor",
        icon="mdi:weather-rainy",
        entity_category=EntityCategory.CONFIG,
        setting_key="rain_sensor",
        write_key="rainSensor",
        iot=False,  # legacy: plain set_bool_setting
    ),
    NavimowSwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        icon="mdi:account-lock",
        entity_category=EntityCategory.CONFIG,
        setting_key="child_lock",
        write_key="childLock",
        iot=True,
        numeric=False,  # cloud string "1"/"0"
    ),
    NavimowSwitchEntityDescription(
        key="lift_alarm",
        translation_key="lift_alarm",
        icon="mdi:alarm-light",
        entity_category=EntityCategory.CONFIG,
        setting_key="lift_alarm",
        write_key="liftSwitch",
        iot=True,
        numeric=False,  # cloud string "1"/"0"
    ),
    NavimowSwitchEntityDescription(
        key="obstacle_avoidance",
        translation_key="obstacle_avoidance",
        icon="mdi:eye-off-outline",
        entity_category=EntityCategory.CONFIG,
        setting_key="obstacle_avoid",
        write_key="cptSwitch",
        iot=True,
        numeric=True,  # cloud number 1/0
    ),
    NavimowSwitchEntityDescription(
        key="rain_detection",
        translation_key="rain_detection",
        icon="mdi:weather-pouring",
        entity_category=EntityCategory.CONFIG,
        setting_key="rain_detection",
        write_key="rainDetectionSwitch",
        iot=False,  # legacy: plain set_bool_setting
    ),
    NavimowSwitchEntityDescription(
        key="sound",
        translation_key="sound",
        icon="mdi:volume-high",
        entity_category=EntityCategory.CONFIG,
        setting_key="sound",
        write_key="soundSwitch",
        iot=True,
        numeric=False,  # cloud string "1"/"0"
    ),
    NavimowSwitchEntityDescription(
        key="power_saving",
        translation_key="power_saving",
        icon="mdi:leaf",
        entity_category=EntityCategory.CONFIG,
        setting_key="power_saving",
        write_key="lowPowerSet",
        iot=True,
        numeric=True,  # cloud number 1/0
    ),
    NavimowSwitchEntityDescription(
        key="frost_delay",
        translation_key="frost_delay",
        icon="mdi:snowflake-alert",
        entity_category=EntityCategory.CONFIG,
        setting_key="frost_delay",
        write_key="frostSwitch",
        iot=True,
        numeric=True,  # cloud number 1/0
    ),
    NavimowSwitchEntityDescription(
        key="snow_delay",
        translation_key="snow_delay",
        icon="mdi:snowflake",
        entity_category=EntityCategory.CONFIG,
        setting_key="snow_delay",
        write_key="snowSwitch",
        iot=True,
        numeric=True,  # cloud number 1/0
    ),
    NavimowSwitchEntityDescription(
        key="storm_delay",
        translation_key="storm_delay",
        icon="mdi:weather-windy",
        entity_category=EntityCategory.CONFIG,
        setting_key="storm_delay",
        write_key="stormSwitch",
        iot=True,
        numeric=True,  # cloud number 1/0
    ),
    NavimowSwitchEntityDescription(
        key="high_temp_delay",
        translation_key="high_temp_delay",
        icon="mdi:thermometer-high",
        entity_category=EntityCategory.CONFIG,
        setting_key="high_temp_delay",
        write_key="highTempSwitch",
        iot=True,
        numeric=True,  # cloud number 1/0
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Navimow setting switches (only with the optional app login)."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    pro_coordinator = data.get("pro_coordinator")
    if pro_coordinator is None:
        return

    entities: list[NavimowSettingSwitch] = []
    for device in data["devices"]:
        settings = pro_coordinator.settings_for(device.id)
        for description in SWITCHES:
            # Feature-detect: only expose a switch the robot actually reports.
            if settings.get(description.setting_key) is not None:
                entities.append(
                    NavimowSettingSwitch(pro_coordinator, device, description)
                )
    async_add_entities(entities)


class NavimowSettingSwitch(
    CoordinatorEntity[NavimowProCoordinator], SwitchEntity
):
    """A controllable mower setting via the private cloud."""

    entity_description: NavimowSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NavimowProCoordinator,
        device: Any,
        entity_description: NavimowSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._serial = device.id
        # Shows the just-commanded value immediately after a write, until the
        # next poll confirms it (the private API has no push).
        self._optimistic: bool | None = None
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
        if self._optimistic is not None:
            return self._optimistic
        settings = self.coordinator.settings_for(self._serial)
        return settings.get(self.entity_description.setting_key)

    def _handle_coordinator_update(self) -> None:
        # A fresh poll is authoritative: drop the optimistic value.
        self._optimistic = None
        super()._handle_coordinator_update()

    async def _write(self, on: bool) -> None:
        desc = self.entity_description
        client = self.coordinator.client
        if desc.iot:
            # 1) device command first, so the robot actually applies it (the
            #    cloud copy alone is reverted by the robot).
            robot_val: Any = (
                (1 if on else 0) if desc.robot_numeric else ("1" if on else "0")
            )
            await self.coordinator.async_send(
                client.send_setting_device, self._serial, {desc.write_key: robot_val}
            )
            # 2) cloud persist (save-set-data + iot_set).
            await self.coordinator.async_send(
                client.set_iot_bool,
                self._serial,
                self.coordinator.vehicle_type_for(self._serial),
                desc.write_key,
                on,
                desc.numeric,
            )
        else:
            await self.coordinator.async_send(
                client.set_bool_setting, self._serial, desc.write_key, on
            )
        # Show the new value at once; the refresh below confirms it.
        self._optimistic = on
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write(False)
