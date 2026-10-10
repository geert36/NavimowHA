"""Config flow for Navimow integration."""
from __future__ import annotations
import logging
import uuid
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .auth import NavimowOAuth2Implementation
from .const import (
    DOMAIN,
    CLIENT_ID,
    CLIENT_SECRET,
    API_BASE_URL,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    CONF_ZONE_NAMES,
    DEFAULT_ZONE_NAMES,
    CONF_PRO_EMAIL,
    CONF_PRO_PASSWORD,
    CONF_PRO_REGION,
    PRO_API_DATA,
)
from .pro_api import PassportAuthError, PassportError, Tokens, passport
from .pro_api._const import REGION_AUTO, REGIONS

_LOGGER = logging.getLogger(__name__)
_LOGGER.debug("Navimow config_flow module imported")


class NavimowOAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle a Navimow OAuth2 config flow."""

    DOMAIN = DOMAIN
    VERSION = 1

    # Stashed OAuth token data between the OAuth step and the optional
    # private-cloud (pro) login step.
    _oauth_data: dict[str, Any] | None = None

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def oauth2_implementation(self) -> NavimowOAuth2Implementation:
        """Return the OAuth2 implementation."""
        _LOGGER.debug(
            "Creating OAuth2 implementation for domain=%s, client_id_set=%s, client_secret_set=%s",
            DOMAIN,
            bool(CLIENT_ID),
            bool(CLIENT_SECRET),
        )
        implementation = NavimowOAuth2Implementation(
            self.hass, DOMAIN, CLIENT_ID, CLIENT_SECRET
        )
        config_entry_oauth2_flow.async_register_implementation(
            self.hass, DOMAIN, implementation
        )
        _LOGGER.debug("OAuth2 implementation registered for domain=%s", DOMAIN)
        return implementation

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        _LOGGER.debug("Starting OAuth2 flow: source=%s", self.source)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if not CLIENT_ID or not CLIENT_SECRET:
            _LOGGER.error(
                "Missing OAuth2 client configuration: client_id_set=%s, client_secret_set=%s",
                bool(CLIENT_ID),
                bool(CLIENT_SECRET),
            )
            return self.async_abort(
                reason="missing_config",
                description_placeholders={
                    "error": "CLIENT_ID 或 CLIENT_SECRET 未配置，请在 const.py 中配置"
                },
            )

        _LOGGER.debug("Registering OAuth2 implementation before authorize step")
        _ = self.oauth2_implementation
        _LOGGER.debug("Proceeding to OAuth2 authorize step")
        return await super().async_step_user()

    async def async_step_oauth2_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ensure implementation exists before redirect."""
        _LOGGER.debug("Entering oauth2_authorize step")
        _ = self.oauth2_implementation
        return await super().async_step_oauth2_authorize(user_input)

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=None,
            )

        return await super().async_step_user()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Finish OAuth, then offer the optional private-cloud login step."""
        if self.source == config_entries.SOURCE_REAUTH:
            existing_entry = self.entry
            self.hass.config_entries.async_update_entry(
                existing_entry,
                data={
                    **existing_entry.data,
                    **data,
                },
            )
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        # Hold the OAuth result and move on to the optional app-login step for
        # the extra private-cloud sensors.
        self._oauth_data = data
        return await self.async_step_pro_auth()

    def _create_entry(self, pro: dict[str, Any] | None) -> FlowResult:
        """Build the config entry from the OAuth data plus optional pro tokens."""
        entry_data: dict[str, Any] = {
            "auth_implementation": DOMAIN,
            **(self._oauth_data or {}),
            "api_base_url": API_BASE_URL,
            "mqtt_broker": MQTT_BROKER,
            "mqtt_port": MQTT_PORT,
            "mqtt_username": MQTT_USERNAME,
            "mqtt_password": MQTT_PASSWORD,
        }
        if pro:
            entry_data[PRO_API_DATA] = pro
        return self.async_create_entry(title="Navimow", data=entry_data)

    async def async_step_pro_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Optional second login to the Navimow app's private cloud.

        Leaving both fields empty skips it; the integration then runs on the
        official OAuth API only (no blade/schedule/settings sensors).
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            email = (user_input.get(CONF_PRO_EMAIL) or "").strip()
            password = user_input.get(CONF_PRO_PASSWORD) or ""
            region_choice = user_input.get(CONF_PRO_REGION) or REGION_AUTO

            if not email and not password:
                return self._create_entry(None)  # skipped
            if not email or not password:
                errors["base"] = "pro_incomplete"
            else:
                region = None if region_choice == REGION_AUTO else region_choice
                try:
                    tokens: Tokens = await self.hass.async_add_executor_job(
                        passport.login, email, password, region
                    )
                except PassportAuthError:
                    errors["base"] = "pro_invalid_auth"
                except PassportError:
                    errors["base"] = "pro_cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error during private-cloud login")
                    errors["base"] = "pro_unknown"
                else:
                    return self._create_entry(
                        {
                            CONF_PRO_EMAIL: email,
                            "access_token": tokens.access_token,
                            "refresh_token": tokens.refresh_token,
                            "uuid": tokens.uuid,
                            CONF_PRO_REGION: tokens.region or "",
                            "device_id": uuid.uuid4().hex,
                        }
                    )

        schema = vol.Schema(
            {
                vol.Optional(CONF_PRO_EMAIL, default=""): str,
                vol.Optional(CONF_PRO_PASSWORD, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_PRO_REGION, default=REGION_AUTO): vol.In(
                    [REGION_AUTO, *REGIONS]
                ),
            }
        )
        return self.async_show_form(
            step_id="pro_auth", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return NavimowOptionsFlowHandler(config_entry)


class NavimowOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Navimow options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ZONE_NAMES,
                        default=self._config_entry.options.get(
                            CONF_ZONE_NAMES, DEFAULT_ZONE_NAMES
                        ),
                    ): str,
                }
            ),
        )
