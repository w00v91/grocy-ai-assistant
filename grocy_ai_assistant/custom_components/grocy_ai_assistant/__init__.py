import logging
import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
DOMAIN = "grocy_ai_assistant"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt die Integration auf."""
    
    # Konfiguration laden
    conf = {**entry.data, **entry.options}
    api_key = conf.get("api_key")
    grocy_api_key = conf.get("grocy_api_key")

    if not api_key:
        _LOGGER.error("Kein API-Key in der Konfiguration gefunden!")
        return False
        
    if not grocy_api_key:
        _LOGGER.error("Kein Grocy-API-Key in der Konfiguration gefunden!")
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = conf
    
    # --- DIENST 1: Produkt via KI anlegen ---
    async def add_product_via_ai_service(call):
        product_name = call.data.get("name")
        _LOGGER.info(f"KI-Analyse startet für: {product_name}")

        ai_url = "http://localhost:8000/api/analyze_product"
        headers = {"Authorization": f"Bearer {api_key}"}

        async with aiohttp.ClientSession() as session:
            try:
                # 1. KI-Add-on fragen
                async with session.post(ai_url, json={"name": product_name}, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error(f"KI-Add-on Fehler: {resp.status}")
                        return
                    
                    res_data = await resp.json()
                    product_attrs = res_data.get("product_data")
                    
                    # In der __init__.py nach dem erfolgreichen KI-Call:
                    response_text = f"Produkt '{product_name}' wurde analysiert und mit lokalem Bild in Grocy angelegt."

                    # Setze den Status des Response-Sensors direkt
                    hass.states.async_set(
                        f"sensor.{DOMAIN}_response", 
                        response_text,
                        {"friendly_name": "Grocy AI Response", "icon": "mdi:robot-happy"}
)

                # 2. An Grocy senden
                grocy_url = "http://a0d49513_grocy/api/objects/products"
                grocy_headers = {
                    "GROCY-API-KEY": grocy_api_key, # <--- BITTE ERSETZEN
                    "Content-Type": "application/json"
                }

                async with session.post(grocy_url, json=product_attrs, headers=grocy_headers) as grocy_resp:
                    if grocy_resp.status in [200, 201]:
                        _LOGGER.info(f"Produkt {product_name} erfolgreich angelegt!")
                    else:
                        _LOGGER.error(f"Grocy Fehler: {await grocy_resp.text()}")

            except Exception as e:
                _LOGGER.error(f"Fehler im add_product Ablauf: {e}")

    # --- DIENST 2: Einfache KI Abfrage ---
    async def ask_ai_service(call):
        prompt = call.data.get("prompt", "Hallo")
        url = "http://localhost:8000/api/process"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json={"prompt": prompt}, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        hass.states.async_set("sensor.grocy_ai_response", result.get("answer", "Keine Antwort"))
            except Exception as e:
                _LOGGER.error(f"Fehler im ask_ai Ablauf: {e}")

    # Registrierung der Dienste
    hass.services.async_register(DOMAIN, "add_product_via_ai", add_product_via_ai_service)
    hass.services.async_register(DOMAIN, "ask_ai", ask_ai_service)

    # Listener & Plattformen
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "text"])

    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok