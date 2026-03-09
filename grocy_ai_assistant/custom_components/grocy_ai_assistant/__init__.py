import logging
import aiohttp
import base64
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt die Integration auf."""
    
    conf = {**entry.data, **entry.options}
    api_key = conf.get("api_key")
    grocy_api_key = conf.get("grocy_api_key")
    debug_enabled = conf.get("debug_mode", False)

    if not api_key or not grocy_api_key:
        _LOGGER.error("API-Keys fehlen in der Konfiguration!")
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = conf
    
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    async def add_product_via_ai_service(call):
        # WICHTIG: Lade die Daten HIER frisch aus dem Entry, 
        # damit Änderungen am Debug-Modus ohne Neustart greifen!
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        active_conf = {**current_entry.data, **current_entry.options}
        
        debug_enabled = active_conf.get("debug_mode", False)
        api_key = active_conf.get("api_key")
        grocy_api_key = active_conf.get("grocy_api_key")

        _LOGGER.info(f"Dienst getriggert! Debug: {debug_enabled}")
        product_name = call.data.get("name")
        _LOGGER.info(f"Name aus Call: {product_name}")
        if not product_name:
            state = hass.states.get(f"text.{DOMAIN}_produkt_name")
            product_name = state.state if state else ""

        if not product_name:
            _LOGGER.warning("Kein Produktname angegeben.")
            return

        _LOGGER.info(f"KI-Analyse startet für: {product_name}")
        hass.states.async_set(f"sensor.{DOMAIN}_response", "KI arbeitet... (Bild & Daten)", {"icon": "mdi:progress-clock"})

        # Nutze die IP oder den Hostname aus der Konfiguration
        ai_url = f"http://71139b3d-grocy-ai-assistant:8000/api/analyze_product"
        headers = {"Authorization": f"Bearer {api_key}"}
        timeout = aiohttp.ClientTimeout(total=180) # Erhöht auf 3 Min für langsame GPUs

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # --- SCHRITT 1: KI-Analyse ---
                async with session.post(ai_url, json={"name": product_name}, headers=headers) as resp:
                    if resp.status != 200:
                        raise Exception(f"KI-Add-on antwortet mit Status {resp.status}")
                    
                    res_data = await resp.json()
                    product_attrs = res_data.get("product_data")
                    image_b64 = res_data.get("image_base64")

                if not product_attrs:
                    raise Exception("KI hat keine Produktdaten geliefert.")
                    
                if debug_enabled:
                    _LOGGER.info("🧪 DEBUG MODE AKTIV: Simulation des Grocy-Imports")
                    _LOGGER.info(f"🧠 KI-Analyse Ergebnis: {res_data}")
                    
                    # Benachrichtigung im HA Dashboard anzeigen statt Import
                    hass.components.persistent_notification.create(
                        f"KI Ergebnis (Simulation):\n{res_data}",
                        title="Grocy AI Debug"
                    )
                    return True # Beende hier, kein POST an Grocy

                # --- SCHRITT 2: Produkt in Grocy erstellen ---
                grocy_url = "http://homeassistant.local:8123/api/grocy/objects/products"
                grocy_headers = {"GROCY-API-KEY": grocy_api_key, "Content-Type": "application/json"}
                
                async with session.post(grocy_url, json=product_attrs, headers=grocy_headers) as g_resp:
                    if g_resp.status not in [200, 201]:
                        error_text = await g_resp.text()
                        raise Exception(f"Grocy API Fehler: {error_text}")
                    
                    grocy_res_data = await g_resp.json()
                    new_id = grocy_res_data.get('created_object_id')

                # --- SCHRITT 3: Optionaler Bild-Upload ---
                image_success = False
                if image_b64 and new_id:
                    try:
                        file_name = f"product_{new_id}.png"
                        img_bytes = base64.b64decode(image_b64)
                        upload_path_b64 = base64.b64encode(file_name.encode()).decode()
                        upload_url = f"http://homeassistant.local:8123/api/grocy/files/productpictures/{upload_path_b64}"
                        
                        # Upload Bild
                        img_resp = await session.put(upload_url, data=img_bytes, headers={"GROCY-API-KEY": grocy_api_key})
                        
                        if img_resp.status in [200, 201, 204]:
                            # Verknüpfung Bild <-> Produkt
                            update_url = f"http://homeassistant.local:8123/api/grocy/objects/products/{new_id}"
                            await session.put(update_url, json={"picture_file_name": file_name}, headers=grocy_headers)
                            image_success = True
                        else:
                            _LOGGER.warning(f"Bild-Upload fehlgeschlagen (Status {img_resp.status})")
                    except Exception as img_err:
                        _LOGGER.error(f"Fehler bei Bild-Verarbeitung: {img_err}")

                # --- ABSCHLUSS & FEEDBACK ---
                if image_success:
                    final_msg = f"Erfolg: '{product_name}' mit Bild angelegt!"
                else:
                    final_msg = f"Teilerfolg: '{product_name}' ohne Bild angelegt."
                
                hass.states.async_set(f"sensor.{DOMAIN}_response", final_msg, {"icon": "mdi:check-circle"})
                hass.states.async_set(f"text.{DOMAIN}_produkt_name", "")

            except Exception as e:
                _LOGGER.error(f"Fehler im Ablauf: {e}")
                hass.states.async_set(f"sensor.{DOMAIN}_response", f"Fehler: {str(e)[:50]}...", {"icon": "mdi:alert-circle"})

    # --- DIENST 2: Einfache Abfrage ---
    async def ask_ai_service(call):
        prompt = call.data.get("prompt", "Hallo")
        url = "http://71139b3d-grocy-ai-assistant:8000/api/process"
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
    
async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Wird aufgerufen, wenn die Optionen im UI aktualisiert wurden."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "text"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok