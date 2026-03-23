import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .entity import build_device_info
from .runtime import (
    RUNTIME_PRODUCT_INPUT,
    async_runtime_signal,
    async_set_product_input_value,
    get_product_input_value,
)

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
        self._attr_name = "Grocy AI Produkt Name"
        self._attr_unique_id = f"{entry.entry_id}_product_input"
        self._attr_icon = "mdi:cart-plus"
        self._attr_native_value = ""

    async def async_added_to_hass(self) -> None:
        self._attr_native_value = get_product_input_value(
            self.hass, self._entry.entry_id
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                async_runtime_signal(self._entry.entry_id, RUNTIME_PRODUCT_INPUT),
                self._handle_runtime_update,
            )
        )

    def _handle_runtime_update(self) -> None:
        self._attr_native_value = get_product_input_value(
            self.hass, self._entry.entry_id
        )
        _LOGGER.debug(
            "Updated product input text from runtime (length=%s)",
            len(self._attr_native_value),
        )
        self.async_write_ha_state()

    async def async_set_value(self, value: str) -> None:
        if hasattr(self, "hass"):
            async_set_product_input_value(self.hass, self._entry.entry_id, value)
            return

        self._attr_native_value = value
        _LOGGER.debug("Updated product input text (length=%s)", len(value))
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._attr_native_value

    @property
    def device_info(self):
        return build_device_info(self._entry.entry_id)
