"""Sensor platform for Navimow integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NavimowCoordinator


@dataclass(frozen=True, kw_only=True)
class NavimowSensorEntityDescription(SensorEntityDescription):
    """Describes Navimow sensor entity."""

    value_fn: Callable[[NavimowCoordinator], Any]
    attributes_fn: Callable[[NavimowCoordinator], dict[str, Any]] | None = None


SENSOR_DESCRIPTIONS: tuple[NavimowSensorEntityDescription, ...] = (
    NavimowSensorEntityDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: (
            state.battery if (state := coordinator.get_device_state()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="signal_strength",
        name="Signal strength",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: (
            state.signal_strength if (state := coordinator.get_device_state()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="error_code",
        name="Error code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: (
            state.error.get("code")
            if (state := coordinator.get_device_state()) and state.error
            else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="telemetry",
        name="Telemetry",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:radio-tower",
        value_fn=lambda coordinator: (
            state.state if (state := coordinator.get_device_state()) else None
        ),
        attributes_fn=lambda coordinator: _build_telemetry_attributes(coordinator),
    ),
)


def _build_telemetry_attributes(coordinator: NavimowCoordinator) -> dict[str, Any]:
    """Expose raw MQTT-derived data for troubleshooting and feature discovery."""
    state = coordinator.get_device_state()
    attrs = coordinator.get_device_attributes()

    telemetry: dict[str, Any] = {}
    if state:
        telemetry["timestamp"] = state.timestamp
        telemetry["status"] = state.state
        if state.battery is not None:
            telemetry["battery"] = state.battery
        if state.signal_strength is not None:
            telemetry["signal_strength"] = state.signal_strength
        if state.position:
            telemetry["position"] = state.position
        if state.error:
            telemetry["error"] = state.error
        if state.metrics:
            telemetry["metrics"] = state.metrics
    if attrs and attrs.attributes:
        telemetry["attributes"] = attrs.attributes
    return telemetry


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Navimow sensors from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    devices = data["devices"]
    coordinators: dict[str, NavimowCoordinator] = data["coordinators"]

    entities: list[NavimowSensor] = []
    for device in devices:
        coordinator = coordinators[device.id]
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                NavimowSensor(
                    coordinator=coordinator,
                    entity_description=description,
                )
            )
    async_add_entities(entities)


class NavimowSensor(CoordinatorEntity[NavimowCoordinator], SensorEntity):
    """Representation of a Navimow sensor."""

    entity_description: NavimowSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NavimowCoordinator,
        entity_description: NavimowSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description

        device = coordinator.device
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
    def available(self) -> bool:
        if self.coordinator.get_device_state() is not None:
            return True
        return super().available

    @property
    def native_value(self) -> Any:
        """Return sensor value from coordinator."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return optional debug attributes for this sensor."""
        if self.entity_description.attributes_fn is None:
            return {}
        return self.entity_description.attributes_fn(self.coordinator)
