"""Sensor platform for Navimow integration."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfArea
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
        key="vehicle_state",
        name="Vehicle state",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.get_vehicle_state_label(),
    ),
    NavimowSensorEntityDescription(
        key="operating_mode",
        name="Operating mode",
        value_fn=lambda coordinator: coordinator.get_operating_mode(),
        attributes_fn=lambda coordinator: _build_operating_mode_attributes(coordinator),
    ),
    NavimowSensorEntityDescription(
        key="zone",
        name="Zone",
        icon="mdi:map-marker",
        value_fn=lambda coordinator: coordinator.get_zone_label(),
        attributes_fn=lambda coordinator: _build_zone_attributes(coordinator),
    ),
    NavimowSensorEntityDescription(
        key="mowing_percentage",
        name="Mowing percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _active_mowing_location_value(
            coordinator, "mowing_percentage"
        ),
        attributes_fn=lambda coordinator: _build_mowing_progress_attributes(coordinator),
    ),
    NavimowSensorEntityDescription(
        key="subtotal_area",
        name="Subtotal area",
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _active_mowing_location_value(
            coordinator, "subtotal_area"
        ),
    ),
    NavimowSensorEntityDescription(
        key="mowing_week_area",
        name="Mowing week area",
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _active_mowing_location_value(
            coordinator, "mowing_week_area"
        ),
    ),
    NavimowSensorEntityDescription(
        key="mow_start_type",
        name="Mow start type",
        value_fn=lambda coordinator: _active_mowing_location_value(
            coordinator, "mow_start_type"
        ),
        attributes_fn=lambda coordinator: _build_mow_start_type_attributes(coordinator),
    ),
    NavimowSensorEntityDescription(
        key="position_x",
        name="Position X",
        native_unit_of_measurement="m",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: (
            location.get("x") if (location := coordinator.get_device_location()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="position_y",
        name="Position Y",
        native_unit_of_measurement="m",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: (
            location.get("y") if (location := coordinator.get_device_location()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="heading",
        name="Heading",
        native_unit_of_measurement="°",
        icon="mdi:compass",
        value_fn=lambda coordinator: (
            round(math.degrees(location["theta"]) % 360, 1)
            if (location := coordinator.get_device_location())
            and location.get("theta") is not None
            else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="telemetry",
        name="Telemetry",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:radio-tower",
        value_fn=lambda coordinator: (
            state.state
            if (state := coordinator.get_device_state())
            else coordinator.get_vehicle_state_label()
        ),
        attributes_fn=lambda coordinator: _build_telemetry_attributes(coordinator),
    ),
)


def _build_zone_attributes(coordinator: NavimowCoordinator) -> dict[str, Any]:
    """Return both the friendly zone label and raw partition ids."""
    location = coordinator.get_device_location()
    if not location:
        return {}
    return {
        "partition": location.get("partition"),
        "partition_ids": location.get("partition_ids"),
    }


def _active_mowing_location_value(
    coordinator: NavimowCoordinator, key: str
) -> Any | None:
    """Return mowing progress fields only for active mowing sessions."""
    if coordinator.is_mapping_mode():
        return None
    location = coordinator.get_device_location()
    if not location:
        return None
    return location.get(key)


def _build_operating_mode_attributes(coordinator: NavimowCoordinator) -> dict[str, Any]:
    """Return the raw operating mode alongside the mapped entity state."""
    state = coordinator.get_device_state()
    return {
        "raw_state": coordinator.get_raw_state(),
        "entity_state": state.state if state else None,
        "is_mapping": coordinator.is_mapping_mode(),
    }


def _build_mowing_progress_attributes(
    coordinator: NavimowCoordinator,
) -> dict[str, Any]:
    """Return raw mowing-progress fields from the realtime payload."""
    if coordinator.is_mapping_mode():
        return {}
    location = coordinator.get_device_location()
    if not location:
        return {}
    return {
        "current_mow_boundary": location.get("current_mow_boundary"),
        "current_mow_progress": location.get("current_mow_progress"),
        "subtotal_area": location.get("subtotal_area"),
        "mowing_week_area": location.get("mowing_week_area"),
        "mow_action": location.get("mow_action"),
        "mow_start_type": location.get("mow_start_type"),
        "mow_progress_time": location.get("mow_progress_time"),
        "mow_progress_time_iso": location.get("mow_progress_time_iso"),
    }


def _build_mow_start_type_attributes(
    coordinator: NavimowCoordinator,
) -> dict[str, Any]:
    """Return a readable hint for the mow start type code."""
    if coordinator.is_mapping_mode():
        return {}
    location = coordinator.get_device_location()
    if not location:
        return {}

    mow_start_type = location.get("mow_start_type")
    if mow_start_type is None:
        return {}

    label = _mow_start_type_label(mow_start_type)
    return {"label": label} if label else {}


def _mow_start_type_label(value: Any) -> str | None:
    """Map known mow start type codes to readable labels."""
    mapping = {
        1: "manual",
    }
    return mapping.get(value)


def _build_telemetry_attributes(coordinator: NavimowCoordinator) -> dict[str, Any]:
    """Expose raw MQTT-derived data for troubleshooting and feature discovery."""
    state = coordinator.get_device_state()
    event = coordinator.get_device_event()
    attrs = coordinator.get_device_attributes()
    location = coordinator.get_device_location()
    meta = coordinator.get_device_meta()
    debug = coordinator.get_device_debug()

    telemetry: dict[str, Any] = {}
    if state:
        telemetry["timestamp"] = state.timestamp
        telemetry["status"] = state.state
        telemetry["operating_mode"] = coordinator.get_operating_mode()
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
    if event:
        telemetry["event"] = {
            "timestamp": event.timestamp,
            "type": event.type,
            "event": event.event,
            "level": event.level,
            "message": event.message,
            "params": event.params,
        }
    if attrs and attrs.attributes:
        telemetry["attributes"] = attrs.attributes
    if location:
        telemetry["location"] = location
        telemetry["zone_label"] = coordinator.get_zone_label()
        telemetry["vehicle_state_label"] = coordinator.get_vehicle_state_label()
    if meta:
        telemetry["meta"] = meta
    if debug and any(value is not None for value in debug.values()):
        telemetry["debug"] = debug
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
        if self.coordinator.get_device_location() is not None:
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
