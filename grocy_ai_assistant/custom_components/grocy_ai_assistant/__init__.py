import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import panel
from .addon_client import AddonClient
from .const import DEFAULT_ADDON_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {**entry.data, **entry.options}

    if not hass.data[DOMAIN].get("_panel_registered"):
        panel_url = hass.data[DOMAIN][entry.entry_id].get(
            "addon_base_url", DEFAULT_ADDON_BASE_URL
        )
        await panel.async_setup(hass, panel_url)
        hass.data[DOMAIN]["_panel_registered"] = True

    async def add_product_via_ai_service(call):
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        active_conf = {**current_entry.data, **current_entry.options}
        product_name = (call.data.get("name") or "").strip()
        if not product_name:
            state = hass.states.get(f"text.{DOMAIN}_produkt_name")
            product_name = (state.state if state else "").strip()

        if not product_name:
            hass.states.async_set(
                f"sensor.{DOMAIN}_response",
                "Kein Produktname übergeben",
                {"icon": "mdi:alert-circle"},
            )
            return

        client = AddonClient(
            active_conf.get("addon_base_url", DEFAULT_ADDON_BASE_URL),
            active_conf.get("api_key", ""),
        )

        hass.states.async_set(
            f"sensor.{DOMAIN}_response",
            "KI analysiert…",
            {"icon": "mdi:progress-clock"},
        )

        try:
            payload = await client.dashboard_search(product_name)
            if payload.get("_http_status") != 200:
                raise RuntimeError(payload.get("detail") or "Unbekannter API-Fehler")

            hass.states.async_set(
                f"sensor.{DOMAIN}_response",
                payload.get("message", "Vorgang abgeschlossen"),
                {"icon": "mdi:check-circle"},
            )
            hass.states.async_set(f"text.{DOMAIN}_produkt_name", "")
        except Exception as error:
            _LOGGER.error("Fehler beim Add-on Aufruf: %s", error)
            hass.states.async_set(
                f"sensor.{DOMAIN}_response",
                f"Fehler: {error}",
                {"icon": "mdi:alert-circle"},
            )

    hass.services.async_register(
        DOMAIN, "add_product_via_ai", add_product_via_ai_service
    )
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "text"])
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor", "text"])
