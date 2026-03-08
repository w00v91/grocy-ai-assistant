import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Diese Konstante muss mit deiner Domain übereinstimmen
DOMAIN = "grocy_ai_assistant"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt die Integration basierend auf einem Config Entry auf."""
    _LOGGER.info("Initialisiere Grocy AI Assistant Integration")

    # Hier kannst du Daten speichern, die in der ganzen Integration verfügbar sein sollen
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Falls du Sensoren oder andere Plattformen hast, lade sie hier:
    # await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration entfernt wird."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok