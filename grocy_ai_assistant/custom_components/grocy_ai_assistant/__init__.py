import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Diese Konstante muss mit deiner Domain übereinstimmen
DOMAIN = "grocy_ai_assistant"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt die Integration auf."""
    
    # Kombiniere data und options (Options überschreiben Data)
    conf = {**entry.data, **entry.options}
    
    # API-Key auslesen
    api_key = conf.get("api_key")
    ollama_url = conf.get("ollama_url", "http://localhost:11434")

    if not api_key:
        _LOGGER.error("Kein API-Key gefunden!")
        return False

    # Speichere die bereinigte Konfiguration in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = conf

    # Listener registrieren: Wenn Optionen geändert werden, Integration neu laden
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Plattformen (z.B. Sensor) laden
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Wird aufgerufen, wenn Optionen aktualisiert wurden."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration entfernt wird."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok