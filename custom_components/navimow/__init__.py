"""The Navimow integration."""
import asyncio
import json
import logging
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
)
from .location import location_topic, parse_location_payload, position_topic
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)
_LOGGER.debug("Navimow module imported (__init__.py)")

PLATFORMS: list[Platform] = [
    Platform.DEVICE_TRACKER,
    Platform.LAWN_MOWER,
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Navimow component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("Navimow async_setup called, registering OAuth2 implementation")
    config_entry_oauth2_flow.async_register_implementation(
        hass,
        DOMAIN,
        NavimowOAuth2Implementation(
            hass,
            DOMAIN,
            CLIENT_ID,
            CLIENT_SECRET,
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Navimow from a config entry."""
    from mower_sdk.api import MowerAPI
    from mower_sdk.errors import MowerAPIError
    from mower_sdk.sdk import NavimowSDK

    from .coordinator import NavimowCoordinator

    hass.data.setdefault(DOMAIN, {})

    def _mask_secret(value: str | None) -> str:
        if not value:
            return "<empty>"
        if len(value) <= 4:
            return "*" * len(value)
        return f"{value[:2]}***{value[-2:]}"

    try:
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
        if not isinstance(implementation, NavimowOAuth2Implementation):
            raise ConfigEntryAuthFailed("Invalid OAuth2 implementation")

        oauth_session = config_entry_oauth2_flow.OAuth2Session(
            hass, entry, implementation
        )

        token: dict[str, Any] | None = None
        if hasattr(oauth_session, "async_get_valid_token"):
            try:
                token = await oauth_session.async_get_valid_token()
            except AttributeError:
                token = None
        if not token and hasattr(oauth_session, "async_ensure_token_valid"):
            await oauth_session.async_ensure_token_valid()
            token = oauth_session.token
        if not token and hasattr(oauth_session, "async_get_access_token"):
            access_token_value = await oauth_session.async_get_access_token()
            token = {"access_token": access_token_value} if access_token_value else None
        if not token:
            token = entry.data.get("token")
        if not token:
            raise ConfigEntryAuthFailed("No valid token available")
        access_token = token.get("access_token")
        if not access_token:
            raise ConfigEntryAuthFailed("No access token in token data")

        api = MowerAPI(
            session=async_get_clientsession(hass),
            token=access_token,
            base_url=entry.data.get("api_base_url", API_BASE_URL),
        )

        try:
            devices = await api.async_get_devices()
            _LOGGER.info("Discovered %d Navimow device(s)", len(devices))
        except MowerAPIError as err:
            _LOGGER.error("Failed to discover devices: %s", err)
            raise ConfigEntryNotReady(f"Failed to discover devices: {err}") from err
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Authentication failed during device discovery: %s", err)
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

        if not devices:
            _LOGGER.warning("No Navimow devices found")

        try:
            mqtt_info = await api.async_get_mqtt_user_info()
        except MowerAPIError as err:
            _LOGGER.error("Failed to get MQTT info: %s", err)
            raise ConfigEntryNotReady(f"Failed to get MQTT info: {err}") from err

        mqtt_host = mqtt_info.get("mqttHost") or entry.data.get(
            "mqtt_broker", MQTT_BROKER
        )
        mqtt_url = mqtt_info.get("mqttUrl")
        mqtt_username = mqtt_info.get("userName") or entry.data.get(
            "mqtt_username", MQTT_USERNAME
        )
        mqtt_password = mqtt_info.get("pwdInfo") or entry.data.get(
            "mqtt_password", MQTT_PASSWORD
        )
        mqtt_port = 443 if mqtt_url else entry.data.get("mqtt_port", MQTT_PORT)
        ws_path = mqtt_url
        if mqtt_url:
            parsed = urlparse(mqtt_url)
            if parsed.scheme in ("ws", "wss") and parsed.hostname:
                if not mqtt_host:
                    mqtt_host = parsed.hostname
                if parsed.port:
                    mqtt_port = parsed.port
                ws_path = parsed.path or "/"
                if parsed.query:
                    ws_path = f"{ws_path}?{parsed.query}"
        auth_headers = {"Authorization": f"Bearer {access_token}"} if ws_path else None

        _LOGGER.info(
            "MQTT connection parameters: broker=%s port=%s mqtt_url=%s ws_path=%s username=%s password=%s auth_header=%s",
            mqtt_host,
            mqtt_port,
            mqtt_url,
            ws_path,
            _mask_secret(mqtt_username),
            _mask_secret(mqtt_password),
            "Bearer <masked>" if auth_headers else "<none>",
        )

        _location_cache: dict[str, dict[str, Any]] = {}
        _location_coordinators: dict[str, NavimowCoordinator] = {}
        _mqtt_refresh_lock = asyncio.Lock()
        _unload_flag: list[bool] = [False]

        def _attach_mqtt_debug_hooks(sdk: NavimowSDK, api: MowerAPI) -> None:
            mqtt = sdk._mqtt
            original_on_message = mqtt.on_message

            def _get_client_id() -> str:
                client_id_bytes = getattr(mqtt.client, "_client_id", b"")
                if isinstance(client_id_bytes, (bytes, bytearray)):
                    return client_id_bytes.decode("utf-8", errors="replace") or "<empty>"
                return str(client_id_bytes) if client_id_bytes else "<empty>"

            def _device_id_from_topic(topic: str) -> str | None:
                parts = topic.split("/")
                if parts and parts[0] == "":
                    parts = parts[1:]
                if len(parts) >= 3 and parts[0] == "downlink" and parts[1] == "vehicle":
                    return parts[2]
                if len(parts) >= 2 and parts[0] == "navimow":
                    return parts[1]
                return None

            def _subscribe_realtime_topics() -> None:
                subscribed = 0
                for device in devices:
                    device_id = getattr(device, "id", None)
                    if not device_id:
                        continue
                    mqtt.client.subscribe(location_topic(device_id))
                    mqtt.client.subscribe(position_topic(device_id))
                    subscribed += 2
                if subscribed:
                    _LOGGER.info(
                        "MQTT subscribed to %d Navimow realtime topic(s)",
                        subscribed,
                    )

            async def _on_connected() -> None:
                _LOGGER.info(
                    "MQTT connected callback: broker=%s port=%s ws_path=%s tls=%s client_id=%s",
                    mqtt.broker,
                    mqtt.port,
                    mqtt.ws_path,
                    mqtt._use_tls,
                    _get_client_id(),
                )

            async def _on_ready() -> None:
                _LOGGER.info(
                    "MQTT ready callback: subscribed to downlink topics on broker=%s port=%s client_id=%s",
                    mqtt.broker,
                    mqtt.port,
                    _get_client_id(),
                )
                _subscribe_realtime_topics()

            async def _on_disconnected() -> None:
                _LOGGER.debug(
                    "MQTT disconnected callback: broker=%s port=%s ws_path=%s tls=%s client_id=%s",
                    mqtt.broker,
                    mqtt.port,
                    mqtt.ws_path,
                    mqtt._use_tls,
                    _get_client_id(),
                )
                if _unload_flag[0]:
                    return
                if _mqtt_refresh_lock.locked():
                    _LOGGER.debug(
                        "MQTT credential refresh already in progress, skipping duplicate disconnect callback"
                    )
                    return
                async with _mqtt_refresh_lock:
                    if _unload_flag[0]:
                        return
                    await _async_refresh_mqtt_credentials(sdk, api)

            async def _on_message(topic: str, payload: bytes, device_id: str) -> None:
                payload_text = (payload or b"").decode("utf-8", errors="replace")
                resolved_device_id = device_id or _device_id_from_topic(topic)
                _LOGGER.debug(
                    "MQTT message received: topic=%s bytes=%d device=%s payload=%s",
                    topic,
                    len(payload or b""),
                    resolved_device_id,
                    payload_text,
                )

                if resolved_device_id and topic == location_topic(resolved_device_id):
                    try:
                        data = json.loads(payload_text)
                    except (TypeError, ValueError):
                        data = None
                    location = parse_location_payload(
                        _location_cache, resolved_device_id, data
                    )
                    if location is not None:
                        coordinator = _location_coordinators.get(resolved_device_id)
                        if coordinator is not None:
                            hass.loop.call_soon_threadsafe(
                                coordinator.ingest_location, location, topic
                            )
                    return

                if resolved_device_id and topic == position_topic(resolved_device_id):
                    try:
                        data = json.loads(payload_text)
                    except (TypeError, ValueError):
                        data = None
                    coordinator = _location_coordinators.get(resolved_device_id)
                    if coordinator is not None and data is not None:
                        hass.loop.call_soon_threadsafe(
                            coordinator.ingest_position, data, topic
                        )
                    return

                if original_on_message is not None:
                    await original_on_message(topic, payload, device_id)

            mqtt.on_connected = _on_connected
            mqtt.on_ready = _on_ready
            mqtt.on_disconnected = _on_disconnected
            mqtt.on_message = _on_message

            def _on_subscribe(_client, _userdata, mid, granted_qos, *args, **kwargs):
                _LOGGER.info(
                    "MQTT subscribed: mid=%s granted_qos=%s broker=%s port=%s client_id=%s",
                    mid,
                    granted_qos,
                    mqtt.broker,
                    mqtt.port,
                    _get_client_id(),
                )

            def _on_log(_client, _userdata, level, buf):
                _LOGGER.debug("MQTT client log: level=%s msg=%s", level, buf)

            mqtt.client.on_subscribe = _on_subscribe
            mqtt.client.on_log = _on_log

        async def _probe_mqtt_status(sdk: NavimowSDK) -> None:
            await asyncio.sleep(5)
            _LOGGER.info("MQTT status probe (5s): connected=%s", sdk.is_connected)
            await asyncio.sleep(25)
            _LOGGER.info("MQTT status probe (30s): connected=%s", sdk.is_connected)

        async def _async_refresh_mqtt_credentials(sdk: NavimowSDK, api: MowerAPI) -> None:
            new_access_token: str | None = None
            new_auth_headers: dict[str, str] | None = None
            try:
                if hasattr(oauth_session, "async_ensure_token_valid"):
                    await oauth_session.async_ensure_token_valid()
                    fresh_token = oauth_session.token
                elif hasattr(oauth_session, "async_get_valid_token"):
                    fresh_token = await oauth_session.async_get_valid_token()
                else:
                    fresh_token = oauth_session.token

                if fresh_token and fresh_token.get("access_token"):
                    new_access_token = fresh_token["access_token"]
                    api.set_token(new_access_token)
                    new_auth_headers = {"Authorization": f"Bearer {new_access_token}"}
            except Exception as err:
                _LOGGER.warning(
                    "Failed to refresh OAuth token before MQTT credential refresh: %s",
                    err,
                )

            try:
                new_mqtt_info = await api.async_get_mqtt_user_info()
            except Exception as err:
                _LOGGER.warning("Failed to refresh MQTT credentials: %s", err)
                return
            new_username = new_mqtt_info.get("userName")
            new_password = new_mqtt_info.get("pwdInfo")
            if new_auth_headers or new_username or new_password:
                def _do_credential_update() -> None:
                    sdk.update_mqtt_credentials(
                        auth_headers=new_auth_headers,
                        username=new_username,
                        password=new_password,
                    )

                await hass.async_add_executor_job(_do_credential_update)
                _LOGGER.info(
                    "MQTT credentials refreshed from server: username=%s",
                    _mask_secret(new_username),
                )

        def _create_sdk(api: MowerAPI) -> NavimowSDK:
            sdk = NavimowSDK(
                broker=mqtt_host,
                port=mqtt_port,
                username=mqtt_username,
                password=mqtt_password,
                ws_path=ws_path,
                auth_headers=auth_headers,
                loop=hass.loop,
                records=devices,
                keepalive_seconds=2400,
                reconnect_min_delay=1,
                reconnect_max_delay=60,
            )
            _LOGGER.info(
                "Invoking SDK MQTT connect: broker=%s port=%s ws_path=%s",
                mqtt_host,
                mqtt_port,
                ws_path,
            )
            sdk.connect()
            return sdk

        sdk = await hass.async_add_executor_job(_create_sdk, api)
        _attach_mqtt_debug_hooks(sdk, api)
        async_setup_services(hass, sdk)
        hass.async_create_task(_probe_mqtt_status(sdk))

        coordinators: dict[str, NavimowCoordinator] = {}
        for device in devices:
            coordinator = NavimowCoordinator(
                hass=hass,
                sdk=sdk,
                api=api,
                device=device,
                config_entry=entry,
                oauth_session=oauth_session,
            )
            await coordinator.async_setup()
            await coordinator.async_config_entry_first_refresh()
            coordinators[device.id] = coordinator
            _location_coordinators[device.id] = coordinator
            if device.id in _location_cache:
                coordinator.ingest_location(_location_cache[device.id])

        hass.data[DOMAIN][entry.entry_id] = {
            "sdk": sdk,
            "api": api,
            "devices": devices,
            "coordinators": coordinators,
            "oauth_session": oauth_session,
            "unload_flag": _unload_flag,
        }

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        return True

    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        _LOGGER.exception("Error setting up Navimow integration: %s", err)
        raise ConfigEntryNotReady(f"Error setting up integration: {err}") from err


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            data = hass.data[DOMAIN][entry.entry_id]
            if "unload_flag" in data:
                data["unload_flag"][0] = True
            sdk = data.get("sdk")
            if sdk:
                try:
                    sdk.disconnect()
                except Exception as err:
                    _LOGGER.warning("Error disconnecting MQTT: %s", err)

            hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
