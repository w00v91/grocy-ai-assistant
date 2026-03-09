import logging
import aiohttp
import base64
import time  # Für die Performance-Messung
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt die Integration auf."""
    
    # Registriere den Listener für Konfigurationsänderungen (Zahnrad)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    hass.data.setdefault(DOMAIN, {})
    
    # --- DIENST 1: Produkt via KI hinzufügen ---
    async def add_product_via_ai_service(call):
        """Hauptdienst zur Analyse und zum Import."""
        
        # Daten JEDES MAL FRISCH aus dem Entry laden
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        active_conf = {**current_entry.data, **current_entry.options}
        
        debug_enabled = active_conf.get("debug_mode", False)
        api_key = active_conf.get("api_key")
        grocy_api_key = active_conf.get("grocy_api_key")

        _LOGGER.info(f"Grocy AI Dienst gestartet (Debug: {debug_enabled})")

        # Produktname ermitteln (aus Call oder Text-Entität)
        product_name = call.data.get("name")
        if not product_name:
            state = hass.states.get(f"text.{DOMAIN}_produkt_name")
            product_name = state.state if state else ""

        if not product_name:
            _LOGGER.warning("Kein Produktname für die Analyse gefunden.")
            return

        hass.states.async_set(f"sensor.{DOMAIN}_response", "KI analysiert...", {"icon": "mdi:progress-clock"})

        # URLs definieren
        ai_url = "http://71139b3d-grocy-ai-assistant:8000/api/analyze_product"
        grocy_base_url = "http://homeassistant.local:9192/api"
        
        headers = {"Authorization": f"Bearer {api_key}"}
        grocy_headers = {
            "GROCY-API-KEY": grocy_api_key, 
            "Content-Type": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=180)
        duration = 0

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # --- SCHRITT 1: KI-Analyse mit Zeitmessung ---
                start_time = time.perf_counter()
                
                async with session.post(ai_url, json={"name": product_name}, headers=headers) as resp:
                    if resp.status != 200:
                        raise Exception(f"KI-Add-on Fehler: Status {resp.status}")
                    
                    res_data = await resp.json()
                    duration = round(time.perf_counter() - start_time, 2)
                    
                    product_attrs = res_data.get("product_data")
                    image_b64 = res_data.get("image_base64")

                # --- DIE DEBUG-WEICHE ---
                if debug_enabled:
                    _LOGGER.info(f"🧪 DEBUG: KI-Analyse dauerte {duration}s. Daten: {product_attrs}")
                    
                    hass.components.persistent_notification.create(
                        f"### 🤖 KI Analyse Debug\n\n"
                        f"**Dauer:** {duration} Sekunden\n"
                        f"**Erkannte Daten:** `{product_attrs}`\n"
                        f"**Bild vorhanden:** {'✅ Ja' if image_b64 else '❌ Nein'}\n\n"
                        f"*Import wurde aufgrund des Debug-Modus gestoppt.*",
                        title="Grocy AI Assistant",
                        notification_id="grocy_ai_debug"
                    )
                    hass.states.async_set(f"sensor.{DOMAIN}_response", f"Debug fertig ({duration}s)", {"icon": "mdi:flask"})
                    return True 

                # --- SCHRITT 2: Produkt in Grocy erstellen ---
                if not product_attrs:
                    raise Exception("KI lieferte keine validen Produktdaten.")

                grocy_url = f"{grocy_base_url}/objects/products"
                async with session.post(grocy_url, json=product_attrs, headers=grocy_headers) as g_resp:
                    if g_resp.status not in [200, 201]:
                        error_text = await g_resp.text()
                        raise Exception(f"Grocy API Fehler: {error_text}")
                    
                    grocy_res_data = await g_resp.json()
                    new_id = grocy_res_data.get('created_object_id')

                # --- SCHRITT 3: Bild-Upload ---
                image_status = "ohne Bild"
                if image_b64 and new_id:
                    try:
                        file_name = f"product_{new_id}.png"
                        img_bytes = base64.b64decode(image_b64)
                        upload_path_b64 = base64.b64encode(file_name.encode()).decode()
                        upload_url = f"{grocy_base_url}/files/productpictures/{upload_path_b64}"
                        
                        img_resp = await session.put(upload_url, data=img_bytes, headers={"GROCY-API-KEY": grocy_api_key})
                        
                        if img_resp.status in [200, 201, 204]:
                            update_url = f"{grocy_base_url}/objects/products/{new_id}"
                            await session.put(update_url, json={"picture_file_name": file_name}, headers=grocy_headers)
                            image_status = "mit Bild"
                    except Exception as img_err:
                        _LOGGER.error(f"Bild-Upload fehlgeschlagen: {img_err}")

                # Erfolgs-Feedback
                final_msg = f"Erfolg: {product_name} {image_status} ({duration}s)"
                hass.states.async_set(f"sensor.{DOMAIN}_response", final_msg, {"icon": "mdi:check-circle"})
                hass.states.async_set(f"text.{DOMAIN}_produkt_name", "")

            except Exception as e:
                _LOGGER.error(f"Fehler im Ablauf: {e}")
                hass.states.async_set(f"sensor.{DOMAIN}_response", f"Fehler nach {duration}s", {"icon": "mdi:alert-circle"})

    # --- DIENST 2: Einfache Abfrage ---
    async def ask_ai_service(call):
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        api_key = current_entry.data.get("api_key")
        prompt = call.data.get("prompt", "Hallo")
        
        async with aiohttp.ClientSession() as session:
            try:
                url = "http://71139b3d-grocy-ai-assistant:8000/api/process"
                async with session.post(url, json={"prompt": prompt}, headers={"Authorization": f"Bearer {api_key}"}) as resp:
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
    
    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Wird aufgerufen, wenn die Optionen aktualisiert werden."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entladen der Integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "text"])
    return unload_ok