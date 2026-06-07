"""Services for Navimow integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from mower_sdk.sdk import NavimowSDK

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_BLADE_HEIGHT = "set_blade_height"

SERVICE_SCHEMA_SET_BLADE_HEIGHT = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("height"): vol.All(vol.Coerce(int), vol.Range(min=10, max=60)),
    }
)


def async_setup_services(hass: HomeAssistant, sdk: NavimowSDK) -> None:
    """Register Navimow services."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_BLADE_HEIGHT):
        return

    async def _handle_set_blade_height(call: ServiceCall) -> None:
        device_id = call.data["device_id"]
        height = call.data["height"]

        try:
            await hass.async_add_executor_job(sdk.set_blade_height, device_id, height)
        except RuntimeError as err:
            raise HomeAssistantError(
                "De maaier heeft nu geen realtime-verbinding."
            ) from err
        except Exception as err:
            _LOGGER.exception(
                "Failed to set blade height for device %s to %s", device_id, height
            )
            raise HomeAssistantError(
                f"Instellen van maaihoogte mislukt: {err}"
            ) from err

        _LOGGER.info(
            "Set blade height for device %s to %s mm via MQTT",
            device_id,
            height,
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BLADE_HEIGHT,
        _handle_set_blade_height,
        schema=SERVICE_SCHEMA_SET_BLA_HEIGHT,
    )
