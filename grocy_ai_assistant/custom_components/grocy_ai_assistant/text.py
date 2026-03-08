from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Setzt die Text-Entität auf."""
    async_add_entities([GrocyProductInput(entry)], True)

class GrocyProductInput(TextEntity):
    """Entität für die Eingabe des Produktnamens."""
    
    def __init__(self, entry):
        self._entry = entry
        self._attr_name = "Grocy AI Produkt Name"
        self._attr_unique_id = f"{entry.entry_id}_product_input"
        self._attr_icon = "mdi:cart-plus"
        self._attr_native_value = ""

    async def async_set_value(self, value: str) -> None:
        """Wird aufgerufen, wenn der Nutzer Text im UI eingibt."""
        self._attr_native_value = value
        self.async_write_ha_state()