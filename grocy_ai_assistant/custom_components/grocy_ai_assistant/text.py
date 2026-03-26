import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import build_device_info
from .runtime_state import (
    RUNTIME_PRODUCT_INPUT,
    async_set_product_input_value,
    dispatcher_signal,
    get_product_input_value,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the text entity."""
    _LOGGER.debug("Setting up text entity for entry %s", entry.entry_id)
    async_add_entities([GrocyProductInput(entry)], True)


class GrocyProductInput(RestoreEntity, TextEntity):
    """Entity for entering the product name."""

    def __init__(self, entry):
        self._entry = entry
        self._attr_translation_key = "product_input"
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry.entry_id}_product_input"
        self._attr_icon = "mdi:cart-plus"
        self._attr_native_value = ""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                dispatcher_signal(self._entry.entry_id, RUNTIME_PRODUCT_INPUT),
                self._handle_value_update,
            )
        )

        runtime_value = get_product_input_value(self.hass, self._entry.entry_id)
        if runtime_value:
            self._attr_native_value = runtime_value
            return

        if last_state := await self.async_get_last_state():
            restored_value = last_state.state or ""
            self._attr_native_value = restored_value
            async_set_product_input_value(
                self.hass, self._entry.entry_id, restored_value
            )

    async def async_set_value(self, value: str) -> None:
        async_set_product_input_value(self.hass, self._entry.entry_id, value)
        _LOGGER.debug("Updated product input text (length=%s)", len(value))

    @callback
    def _handle_value_update(self, value: str) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        return build_device_info(self._entry.entry_id, getattr(self, "hass", None))
