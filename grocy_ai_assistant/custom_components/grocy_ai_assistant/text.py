import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .entity import build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the text entity."""
    _LOGGER.debug("Setting up text entity for entry %s", entry.entry_id)
    async_add_entities([GrocyProductInput(entry)], True)


class GrocyProductInput(TextEntity):
    """Entity for entering the product name."""

    def __init__(self, entry):
        self._entry = entry
        self._attr_translation_key = "product_input"
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry.entry_id}_product_input"
        self._attr_icon = "mdi:cart-plus"
        self._attr_native_value = ""

    async def async_set_value(self, value: str) -> None:
        self._attr_native_value = value
        _LOGGER.debug("Updated product input text (length=%s)", len(value))
        self.async_write_ha_state()

    @property
    def device_info(self):
        return build_device_info(self._entry.entry_id)
