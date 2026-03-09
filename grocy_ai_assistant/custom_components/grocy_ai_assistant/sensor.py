import logging

import aiohttp
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import CONF_API_KEY, CONF_DEBUG_MODE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors based on config entry."""
    _LOGGER.debug("Setting up sensor entities for entry %s", entry.entry_id)
    entities = [GrocyAISensor(entry), GrocyAIResponseSensor(entry)]
    async_add_entities(entities, update_before_add=True)


class GrocyAISensor(SensorEntity):
    """Sensor for add-on availability."""

    def __init__(self, entry):
        self._entry = entry
        self._debug_mode = bool(entry.options.get(CONF_DEBUG_MODE, False))
        self._attr_name = "Grocy AI Status"
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_native_value = "Initialisiere..."
        self._attr_icon = "mdi:robot"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_update(self):
        api_key = self._entry.data.get(CONF_API_KEY)
        url = "http://localhost:8000/api/status"
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        self._attr_native_value = "Online"
                    else:
                        self._attr_native_value = f"Error {resp.status}"
                    if self._debug_mode:
                        _LOGGER.debug("Status check returned %s", resp.status)
        except Exception as err:
            self._attr_native_value = "Offline"
            if self._debug_mode:
                _LOGGER.debug("Status check failed: %s", err)


class GrocyAIResponseSensor(SensorEntity):
    def __init__(self, entry):
        self._entry = entry
        self._attr_name = "Grocy AI Response"
        self._attr_unique_id = f"{entry.entry_id}_response_text"
        self._attr_native_value = "Bereit"
        self._attr_icon = "mdi:comment-text-outline"

    @property
    def device_info(self):
        return {
            "identifiers": {("domain", "grocy_ai_assistant")},
            "name": "Grocy AI Assistant",
            "manufacturer": "Eigene Integration",
        }

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        _LOGGER.info("Response Sensor registriert und bereit.")
