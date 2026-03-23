import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .entity import build_device_info
from .runtime import (
    get_entry_runtime_data,
    get_product_input_value,
    set_product_input_value,
)

_LOGGER = logging.getLogger(__name__)

DATA_PRODUCT_INPUT_ENTITY = "product_input_entity"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the text entity."""
    _LOGGER.debug("Setting up text entity for entry %s", entry.entry_id)
    async_add_entities([GrocyProductInput(entry)], True)


def get_product_input_entity(
    hass: HomeAssistant, entry_id: str
) -> "GrocyProductInput | None":
    """Return the registered product input entity for the entry, if available."""
    entity = get_entry_runtime_data(hass, entry_id).get(DATA_PRODUCT_INPUT_ENTITY)
    return entity if isinstance(entity, GrocyProductInput) else None


async def async_set_product_input_value(
    hass: HomeAssistant, entry_id: str, value: str
) -> None:
    """Update the product input through the TextEntity when it is loaded."""
    entity = get_product_input_entity(hass, entry_id)
    if entity is not None:
        await entity.async_set_value(value)
        return

    set_product_input_value(hass, entry_id, value)


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
        entry_data = get_entry_runtime_data(self.hass, self._entry.entry_id)
        entry_data[DATA_PRODUCT_INPUT_ENTITY] = self
        self.async_on_remove(self._async_unregister_entity)

    def _async_unregister_entity(self) -> None:
        entry_data = get_entry_runtime_data(self.hass, self._entry.entry_id)
        if entry_data.get(DATA_PRODUCT_INPUT_ENTITY) is self:
            entry_data.pop(DATA_PRODUCT_INPUT_ENTITY, None)

    async def async_set_value(self, value: str) -> None:
        normalized_value = str(value)
        self._attr_native_value = normalized_value
        set_product_input_value(self.hass, self._entry.entry_id, normalized_value)
        _LOGGER.debug("Updated product input text (length=%s)", len(normalized_value))
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._attr_native_value

    @property
    def device_info(self):
        return build_device_info(self._entry.entry_id)
