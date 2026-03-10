import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from . import panel
from .addon_client import AddonClient
from .const import DEFAULT_ADDON_BASE_URL, DOMAIN, INTEGRATION_VERSION

_LOGGER = logging.getLogger(__name__)


def _get_entity_id(
    hass: HomeAssistant, entry_id: str, platform: str, unique_id: str, fallback: str
) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        platform, DOMAIN, f"{entry_id}_{unique_id}"
    )
    return entity_id or fallback


def _response_sensor_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "sensor",
        "response_text",
        f"sensor.{DOMAIN}_response",
    )


def _product_input_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "text",
        "product_input",
        f"text.{DOMAIN}_produkt_name",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration."""
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {**entry.data, **entry.options}

    _LOGGER.info("Setting up Grocy AI Assistant for entry %s", entry.entry_id)

    if not hass.data[DOMAIN].get("_panel_registered"):
        panel_url = hass.data[DOMAIN][entry.entry_id].get(
            "addon_base_url", DEFAULT_ADDON_BASE_URL
        )
        await panel.async_setup(hass, panel_url)
        hass.data[DOMAIN]["_panel_registered"] = True

    response_reset_unsubs = hass.data[DOMAIN].setdefault("_response_reset_unsubs", {})

    def _cancel_response_reset() -> None:
        if unsubscribe := response_reset_unsubs.pop(entry.entry_id, None):
            unsubscribe()

    def _set_response_state(
        message: str,
        icon: str = "mdi:comment-text-outline",
        *,
        reset_after: bool = False,
    ) -> None:
        hass.states.async_set(
            _response_sensor_entity_id(hass, entry),
            message,
            {"icon": icon},
        )

        if reset_after:
            _cancel_response_reset()

            @callback
            def _reset_response_state(_now) -> None:
                response_reset_unsubs.pop(entry.entry_id, None)
                hass.states.async_set(
                    _response_sensor_entity_id(hass, entry),
                    "Bereit",
                    {"icon": "mdi:comment-text-outline"},
                )

            response_reset_unsubs[entry.entry_id] = async_call_later(
                hass, 30, _reset_response_state
            )
        else:
            _cancel_response_reset()

    async def add_product_via_ai_service(call):
        """Analyze a product through the add-on and sync it to Grocy shopping list."""
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        if current_entry is None:
            _LOGGER.error("Config entry %s was not found", entry.entry_id)
            return

        active_conf = {**current_entry.data, **current_entry.options}
        product_name = (call.data.get("name") or "").strip()

        if not product_name:
            state = hass.states.get(_product_input_entity_id(hass, entry))
            product_name = (state.state if state else "").strip()

        if not product_name:
            _set_response_state(
                "Kein Produktname übergeben", "mdi:alert-circle", reset_after=True
            )
            return

        client = AddonClient(
            active_conf.get("addon_base_url", DEFAULT_ADDON_BASE_URL),
            active_conf.get("api_key", ""),
            integration_version=INTEGRATION_VERSION,
        )

        _set_response_state("KI analysiert…", "mdi:progress-clock")

        try:
            payload = await client.dashboard_search(product_name)
            if payload.get("_http_status") != 200:
                raise RuntimeError(payload.get("detail") or "Unbekannter API-Fehler")

            _set_response_state(
                payload.get("message", "Vorgang abgeschlossen"),
                "mdi:check-circle",
                reset_after=True,
            )
            hass.states.async_set(_product_input_entity_id(hass, entry), "")
        except Exception as error:
            _LOGGER.error("Fehler beim Add-on Aufruf: %s", error)
            _set_response_state(
                f"Fehler: {error}", "mdi:alert-circle", reset_after=True
            )

    hass.services.async_register(
        DOMAIN, "add_product_via_ai", add_product_via_ai_service
    )

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "text"])
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry after options update."""
    _LOGGER.info("Reloading config entry %s after options update", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration entry."""
    if (
        unsubscribe := hass.data.get(DOMAIN, {})
        .get("_response_reset_unsubs", {})
        .pop(entry.entry_id, None)
    ):
        unsubscribe()

    hass.services.async_remove(DOMAIN, "add_product_via_ai")
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "text"]
    )
    _LOGGER.debug("Unload entry %s result: %s", entry.entry_id, unload_ok)
    return unload_ok
