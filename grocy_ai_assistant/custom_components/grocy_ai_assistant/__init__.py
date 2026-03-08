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
    
async def add_product_via_ai(call):
    """Dienst: Produkt via KI analysieren und in Grocy anlegen."""
    product_name = call.data.get("name")
    _LOGGER.info(f"KI-Analyse gestartet für: {product_name}")

    # URL deines Flask-Add-ons (interner Hostname)
    ai_url = "http://localhost:8000/api/analyze_product"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with aiohttp.ClientSession() as session:
        # 1. Schritt: KI-Add-on nach Daten fragen
        try:
            async with session.post(ai_url, json={"name": product_name}, headers=headers) as resp:
                if resp.status != 200:
                    _LOGGER.error(f"KI-Add-on Fehler: {resp.status}")
                    return
                
                data = await resp.json()
                product_attrs = data.get("product_data")
                _LOGGER.info(f"KI hat Daten geliefert: {product_attrs}")

            # 2. Schritt: Daten an Grocy senden
            # Hinweis: 'a0d49513_grocy' ist der Standard-Hostname des Grocy Add-ons
            grocy_url = "http://a0d49513_grocy/api/objects/products"
            grocy_headers = {
                "GROCY-API-KEY": "DEIN_GROCY_API_KEY", # Hier deinen echten Grocy Key eintragen
                "Content-Type": "application/json"
            }

            async with session.post(grocy_url, json=product_attrs, headers=grocy_headers) as grocy_resp:
                if grocy_resp.status in [200, 201]:
                    _LOGGER.info(f"Erfolg! {product_name} wurde in Grocy angelegt.")
                    hass.bus.async_fire("grocy_ai_success", {"product": product_name})
                else:
                    _LOGGER.error(f"Grocy API Fehler: {await grocy_resp.text()}")

        except Exception as e:
            _LOGGER.error(f"Fehler im Ablauf: {e}")

    # Registrierung des Dienstes in Home Assistant
    hass.services.async_register(DOMAIN, "add_product_via_ai", add_product_via_ai)

    # Weiterleitung an Sensor-Plattform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True
    
async def handle_ask_ai(call):
        prompt = call.data.get("prompt", "Hallo")
        target_sensor = "sensor.grocy_ai_response"
        
        # API Call an dein Add-on (Flask)
        # Wir nutzen hier die interne URL des Add-ons (Hostname)
        url = "http://localhost:8000/api/process" 
        headers = {"Authorization": f"Bearer {entry.data.get('api_key')}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"prompt": prompt}, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    # Antwort in einem Helfer oder Sensor speichern
                    hass.states.async_set(target_sensor, result.get("answer", "Keine Antwort"))

    hass.services.async_register(DOMAIN, "ask_ai", handle_ask_ai)
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