import logging
import aiohttp
from homeassistant.components.sensor import SensorEntity
# Dieser Import hat gefehlt:
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Sensoren basierend auf dem Config Entry einrichten."""
    # Hol die Daten, die wir in der __init__.py gespeichert haben
    conf = hass.data[DOMAIN][entry.entry_id]
    api_key = conf.get("api_key")
    ollama_url = conf.get("ollama_url")

    # Erstelle die Sensor-Instanz
    entities = [
        GrocyAISensor(entry),
        GrocyAIResponseSensor(entry)
    ]
    # Übergebe die Liste an HA
    async_add_entities(entities, update_before_add=True)

class GrocyAISensor(SensorEntity):
    """Sensor für die Erreichbarkeit des Add-ons."""
    
    def __init__(self, entry):
        """Initialisierung nur mit entry."""
        self._entry = entry
        # Wir holen uns die URL direkt aus den Daten des entries
        self._ollama_url = entry.data.get("ollama_url", "http://172.17.0.1:11434/api/generate")
        
        self._attr_name = "Grocy AI Status"
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_native_value = "Initialisiere..."
        self._attr_icon = "mdi:robot"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_update(self):
        """Prüfung der Erreichbarkeit."""
        # Wir nutzen den API-Key aus dem entry
        api_key = self._entry.data.get("api_key")
        # WICHTIG: Port 8000 ist dein Flask-Add-on, nicht Ollama direkt!
        url = "http://localhost:8000/api/status" 
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        self._attr_native_value = "Online"
                    else:
                        self._attr_native_value = f"Error {resp.status}"
        except Exception:
            self._attr_native_value = "Offline"

class GrocyAIResponseSensor(SensorEntity):
    def __init__(self, entry):
        self._entry = entry
        # WICHTIG: Benutze DOMAIN aus const.py oder schreibe "grocy_ai_assistant"
        self._attr_name = "Grocy AI Response"
        self._attr_unique_id = f"{entry.entry_id}_response_text"
        self._attr_native_value = "Bereit" # Startwert geben!
        self._attr_icon = "mdi:comment-text-outline"
        self._attr_entity_category = EntityCategory.SENSOR


    @property
    def device_info(self):
        """Verknüpft den Sensor mit dem 'Gerät' deiner Integration."""
        return {
            "identifiers": {("domain", "grocy_ai_assistant")},
            "name": "Grocy AI Assistant",
            "manufacturer": "Eigene Integration",
        }
        
    # Dieser Sensor wird nicht aktiv 'geupdated', sondern von der __init__.py 'beschrieben'
    @property
    def should_poll(self):
        return False
        
    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn der Sensor zu HA hinzugefügt wird."""
        _LOGGER.info("Response Sensor registriert und bereit.")