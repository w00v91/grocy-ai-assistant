import logging
import aiohttp
import base64
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
DOMAIN = "grocy_ai_assistant"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt die Integration auf."""
    
    conf = {**entry.data, **entry.options}
    api_key = conf.get("api_key")
    grocy_api_key = conf.get("grocy_api_key")

    if not api_key or not grocy_api_key:
        _LOGGER.error("API-Keys fehlen in der Konfiguration!")
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = conf
    
    # --- DIENST 1: Produkt via KI anlegen ---
    async def add_product_via_ai_service(call):
        product_name = call.data.get("name")
        if not product_name:
            # Falls Name leer, versuche aus dem Text-Helfer zu lesen
            state = hass.states.get(f"text.{DOMAIN}_produkt_name")
            product_name = state.state if state else ""

        if not product_name:
            _LOGGER.warning("Kein Produktname angegeben.")
            return

        _LOGGER.info(f"KI-Analyse startet für: {product_name}")
        
        # Feedback im Dashboard
        hass.states.async_set(f"sensor.{DOMAIN}_response", "KI arbeitet... (Bild & Daten)", {"icon": "mdi:progress-clock"})

        ai_url = "http://localhost:8000/api/analyze_product"
        headers = {"Authorization": f"Bearer {api_key}"}
        timeout = aiohttp.ClientTimeout(total=150) # Viel Zeit für die Bildgenerierung

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # 1. KI-Analyse & Bildgenerierung
                async with session.post(ai_url, json={"name": product_name}, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error(f"KI-Add-on Fehler: {resp.status}")
                        hass.states.async_set(f"sensor.{DOMAIN}_response", "Fehler bei KI-Analyse")
                        return
                    
                    res_data = await resp.json()
                    product_attrs = res_data.get("product_data")
                    image_b64 = res_data.get("image_base64")
                
                # 2. Produkt in Grocy erstellen
                grocy_url = "http://a0d49513_grocy/api/objects/products"
                grocy_headers = {"GROCY-API-KEY": grocy_api_key, "Content-Type": "application/json"}
                
                async with session.post(grocy_url, json=product_attrs, headers=grocy_headers) as g_resp:
                    if g_resp.status not in [200, 201]:
                        _LOGGER.error(f"Grocy Produkt Fehler: {await g_resp.text()}")
                        return
                    
                    grocy_res_data = await g_resp.json()
                    new_id = grocy_res_data.get('created_object_id')

                # 3. Bild-Upload (Weg B)
                if image_b64 and new_id:
                    file_name = f"product_{new_id}.png"
                    img_bytes = base64.b64decode(image_b64)
                    
                    # Upload zu Grocy Files
                    upload_path_b64 = base64.b64encode(file_name.encode()).decode()
                    upload_url = f"http://a0d49513_grocy/api/files/productpictures/{upload_path_b64}"
                    
                    await session.put(upload_url, data=img_bytes, headers={"GROCY-API-KEY": grocy_api_key})
                    
                    # Bild dem Produkt zuordnen
                    update_url = f"http://a0d49513_grocy/api/objects/products/{new_id}"
                    await session.put(update_url, json={"picture_file_name": file_name}, headers=grocy_headers)

                # Erfolg melden
                hass.states.async_set(f"sensor.{DOMAIN}_response", f"Erfolg: {product_name} angelegt!", {"icon": "mdi:check-circle"})
                # Textfeld leeren
                hass.states.async_set(f"text.{DOMAIN}_produkt_name", "")

            except Exception as e:
                _LOGGER.error(f"Fehler im Ablauf: {e}")
                hass.states.async_set(f"sensor.{DOMAIN}_response", f"Fehler: {e}")

    # --- DIENST 2: Einfache Abfrage ---
    async def ask_ai_service(call):
        prompt = call.data.get("prompt", "Hallo")
        url = "http://localhost:8000/api/process"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json={"prompt": prompt}, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        hass.states.async_set(f"sensor.{DOMAIN}_response", result.get("answer", "Keine Antwort"))
            except Exception as e:
                _LOGGER.error(f"Fehler bei ask_ai: {e}")

    # Registrierung
    hass.services.async_register(DOMAIN, "add_product_via_ai", add_product_via_ai_service)
    hass.services.async_register(DOMAIN, "ask_ai", ask_ai_service)

    # Plattformen laden
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "text"])
    
    # Start-Status
    hass.states.async_set(f"sensor.{DOMAIN}_response", "System bereit", {"friendly_name": "Grocy AI Response"})

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "text"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok