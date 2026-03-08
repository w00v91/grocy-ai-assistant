import logging
import aiohttp
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Sensoren basierend auf dem Config Entry einrichten."""
    # Hol die Daten, die wir in der __init__.py gespeichert haben
    conf = hass.data[DOMAIN][entry.entry_id]
    api_key = conf.get("api_key")
    ollama_url = conf.get("ollama_url")

    # Erstelle die Sensor-Instanz
    async_add_entities([GrocyAISensor(api_key, ollama_url)], True)

class GrocyAISensor(SensorEntity):
    """Ein Sensor, der den Status der KI-Verbindung anzeigt."""

    def __init__(self, api_key, ollama_url):
        self._api_key = api_key
        self._ollama_url = ollama_url
        self._state = "Initialisierung"
        self._attr_name = "Grocy AI Status"
        self._attr_unique_id = "grocy_ai_status_unique"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        """Holt den aktuellen Status vom Add-on Service."""
        # Beispiel: Test-Anfrage an deinen Flask-Service im Add-on
        url = "http://localhost:8000/api/status" 
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._state = data.get("status", "Verbunden")
                    else:
                        self._state = f"Fehler: {response.status}"
        except Exception as e:
            _LOGGER.error("Fehler beim Update des Grocy AI Sensors: %s", e)
            self._state = "Nicht erreichbar"