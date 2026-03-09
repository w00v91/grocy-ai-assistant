import logging
import aiohttp
import base64
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt die Integration auf."""
    
    # Initiales Laden der Konfiguration
    conf = {**entry.data, **entry.options}
    
    # Registriere den Listener für Konfigurationsänderungen (Zahnrad)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = conf
    
    # --- DIENST 1: Produkt via KI hinzufügen ---
    async def add_product_via_ai_service(call):
        """Hauptdienst zur Analyse und zum Import."""
        
        # WICHTIG: Daten HIER frisch aus dem Entry laden, damit der Debug-Schalter sofort reagiert
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        active_conf = {**current_entry.data, **current_entry.options}
        
        debug_enabled = active_conf.get("debug_mode", False)
        api_key = active_conf.get("api_key")
        grocy_api_key = active_conf.get("grocy_api_key")

        _LOGGER.info(f"Grocy AI Dienst getriggert! (Debug-Modus: {debug_enabled})")

        # Produktname ermitteln
        product_name = call.data.get("name")
        if not product_name:
            state = hass.states.get(f"text.{DOMAIN}_produkt_name")
            product_name = state.state if state else ""

        if not product_name:
            _LOGGER.warning("Kein Produktname vorhanden.")
            return

        hass.states.async_set(f"sensor.{DOMAIN}_response", "KI analysiert...", {"icon": "mdi:progress-clock"})

        # URLs definieren
        ai_url = "http://71139b3d-grocy-ai-assistant:8000/api/analyze_product"
        # Wir nutzen Port 9192, da dieser bei dir funktioniert hat:
        grocy_base_url = "http://homeassistant.local:9192/api"
        
        headers = {"Authorization": f"Bearer {api_key}"}
        grocy_headers = {
            "GROCY-API-KEY": grocy_api_key, 
            "Content-Type": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=180)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # --- SCHRITT 1: KI-Analyse ---
                async with session.post(ai_url, json={"name": product_name}, headers=headers) as resp:
                    if resp.status != 200:
                        raise Exception(f"KI-Add-on Fehler: Status {resp.status}")
                    
                    res_data = await resp.json()
                    product_attrs = res_data.get("product_data")
                    image_b64 = res_data.get("image_base64")

                if not product_attrs:
                    raise Exception("KI lieferte keine Produktdaten.")

                # --- DIE DEBUG-WEICHE ---
                if debug_enabled:
                    _LOGGER.info(f"🧪 DEBUG: KI-Ergebnis erhalten: {product_attrs}")
                    
                    hass.components.persistent_notification.create(
                        f"**KI Analyse Ergebnis (Simulation):**\n\n"
                        f"Daten: `{product_attrs}`\n\n"
                        f"Bild erhalten: {'Ja' if image_b64 else 'Nein'}",
                        title="Grocy AI Debug Mode",
                        notification_id="grocy_ai_debug"
                    )
                    hass.states.async_set(f"sensor.{DOMAIN}_response", "Simulation beendet (siehe Benachrichtigung)", {"icon": "mdi:flask"})
                    return True # Beendet den Dienst hier, kein Import zu Grocy!

                # --- SCHRITT 2: Produkt in Grocy erstellen ---
                grocy_url = f"{grocy_base_url}/objects/products"
                async with session.post(grocy_url, json=product_attrs, headers=grocy_headers) as g_resp:
                    if g_resp.status not in [200, 201]:
                        error_text = await g_resp.text()
                        raise Exception(f"Grocy API Fehler: {error_text}")
                    
                    grocy_res_data = await g_resp.json()
                    new_id = grocy_res_data.get('created_object_id')

                # --- SCHRITT 3: Bild-Upload ---
                image_success = False
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
                            image_success = True
                    except Exception as img_err:
                        _LOGGER.error(f"Bildfehler: {img_err}")

                # Feedback in HA
                final_msg = f"Erfolg: '{product_attrs.get('name')}' angelegt!"
                hass.states.async_set(f"sensor.{DOMAIN}_response", final_msg, {"icon": "mdi:check-circle"})
                hass.states.async_set(f"text.{DOMAIN}_produkt_name", "")

            except Exception as e:
                _LOGGER.error(f"Fehler im Ablauf: {e}")
                hass.states.async_set(f"sensor.{DOMAIN}_response", f"Fehler: {str(e)[:50]}", {"icon": "mdi:alert-circle"})

    # --- DIENST 2: Einfache Abfrage ---
    async def ask_ai_service(call):
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        api_key = current_entry.data.get("api_key")
        
        prompt = call.data.get("prompt", "Hallo")
        url = "http://71139b3d-grocy-ai-assistant:8000/api/process"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json={"prompt": prompt}, headers={"Authorization": f"Bearer {api_key}"}) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        hass.states.async_set(f"sensor.{DOMAIN}_response", result.get("answer", "Keine Antwort"))
            except Exception as e:
                _LOGGER.error(f"Fehler bei ask_ai: {e}")

    # Registrierung der Dienste
    hass.services.async_register(DOMAIN, "add_product_via_ai", add_product_via_ai_service)
    hass.services.async_register(DOMAIN, "ask_ai", ask_ai_service)

    # Plattformen (Sensor & Text) laden
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "text"])
    
    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Wird aufgerufen, wenn Optionen (Zahnrad) geändert werden."""
    _LOGGER.info("Konfiguration wurde geändert, lade Integration neu...")
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entladen der Integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "text"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok