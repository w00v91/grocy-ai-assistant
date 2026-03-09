import base64
import logging

import time

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import panel
from .addon_client import AddonClient
from .const import DEFAULT_ADDON_BASE_URL, DOMAIN
from .const import (
    CONF_API_KEY,
    CONF_DEBUG_MODE,
    CONF_GROCY_API_KEY,
    CONF_GROCY_BASE_URL,
    DEFAULT_GROCY_BASE_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
def _normalize_name(value: str) -> str:
    return (value or "").strip().casefold()


def _is_debug_enabled(config: dict) -> bool:
    return bool(config.get(CONF_DEBUG_MODE, False))


def _debug_log(config: dict, message: str, *args) -> None:
    if _is_debug_enabled(config):
        _LOGGER.debug(message, *args)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration."""
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {**entry.data, **entry.options}

    _LOGGER.info("Setting up Grocy AI Assistant for entry %s", entry.entry_id)

    if not hass.data[DOMAIN].get("_panel_registered"):
        panel_url = hass.data[DOMAIN][entry.entry_id].get(
            "addon_base_url", DEFAULT_ADDON_BASE_URL
        )
        await panel.async_setup(hass, panel_url)
        hass.data[DOMAIN]["_panel_registered"] = True

    async def add_product_via_ai_service(call):
        _LOGGER.debug("Registered Grocy AI panel")

    async def add_product_via_ai_service(call):
        """Main service for product analysis and import."""
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        if current_entry is None:
            _LOGGER.error("Config entry %s was not found", entry.entry_id)
            return

        active_conf = {**current_entry.data, **current_entry.options}
        product_name = (call.data.get("name") or "").strip()
        api_key = active_conf.get(CONF_API_KEY)
        grocy_api_key = active_conf.get(CONF_GROCY_API_KEY)
        grocy_base_url = active_conf.get(CONF_GROCY_BASE_URL, DEFAULT_GROCY_BASE_URL)

        _LOGGER.info("Grocy AI service started")
        _debug_log(active_conf, "Debug mode active for service call")

        product_name = call.data.get("name")
        if not product_name:
            state = hass.states.get(f"text.{DOMAIN}_produkt_name")
            product_name = (state.state if state else "").strip()

        if not product_name:
            hass.states.async_set(
                f"sensor.{DOMAIN}_response",
                "Kein Produktname übergeben",
                {"icon": "mdi:alert-circle"},
            )
            return

        client = AddonClient(
            active_conf.get("addon_base_url", DEFAULT_ADDON_BASE_URL),
            active_conf.get("api_key", ""),
        )

        hass.states.async_set(
            f"sensor.{DOMAIN}_response",
            "KI analysiert…",
            {"icon": "mdi:progress-clock"},
        )

        try:
            payload = await client.dashboard_search(product_name)
            if payload.get("_http_status") != 200:
                raise RuntimeError(payload.get("detail") or "Unbekannter API-Fehler")

            hass.states.async_set(
                f"sensor.{DOMAIN}_response",
                payload.get("message", "Vorgang abgeschlossen"),
                {"icon": "mdi:check-circle"},
            )
            hass.states.async_set(f"text.{DOMAIN}_produkt_name", "")
        except Exception as error:
            _LOGGER.error("Fehler beim Add-on Aufruf: %s", error)
            hass.states.async_set(
                f"sensor.{DOMAIN}_response",
                f"Fehler: {error}",
                {"icon": "mdi:alert-circle"},
            )
            _LOGGER.warning("No product name provided for analysis")
            return

        hass.states.async_set(
            f"sensor.{DOMAIN}_response",
            "KI analysiert...",
            {"icon": "mdi:progress-clock"},
        )

        ai_url = "http://71139b3d-grocy-ai-assistant:8000/api/analyze_product"
        headers = {"Authorization": f"Bearer {api_key}"}
        grocy_headers = {
            "GROCY-API-KEY": grocy_api_key,
            "Content-Type": "application/json",
        }

        _debug_log(active_conf, "Using Grocy base URL: %s", grocy_base_url)

        timeout = aiohttp.ClientTimeout(total=180)
        duration = 0

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                existing_product = None
                async with session.get(
                    f"{grocy_base_url}/objects/products", headers=grocy_headers
                ) as list_resp:
                    if list_resp.status == 200:
                        products = await list_resp.json()
                        normalized_input = _normalize_name(product_name)
                        existing_product = next(
                            (
                                p
                                for p in products
                                if _normalize_name(p.get("name")) == normalized_input
                            ),
                            None,
                        )
                        _debug_log(
                            active_conf, "Loaded %s products from Grocy", len(products)
                        )
                    else:
                        _debug_log(
                            active_conf,
                            "Grocy product list request returned status %s",
                            list_resp.status,
                        )

                if existing_product:
                    product_id = existing_product.get("id")
                    shopping_url = f"{grocy_base_url}/stock/shoppinglist/add-product"
                    payload = {"product_id": product_id, "amount": 1}

                    async with session.post(
                        shopping_url, json=payload, headers=grocy_headers
                    ) as shopping_resp:
                        if shopping_resp.status not in [200, 204]:
                            error_text = await shopping_resp.text()
                            raise Exception(
                                f"Shoppingliste konnte nicht aktualisiert werden: {error_text}"
                            )

                    hass.states.async_set(
                        f"sensor.{DOMAIN}_response",
                        f"Vorhanden: {product_name} zur Einkaufsliste hinzugefügt",
                        {"icon": "mdi:cart-check"},
                    )
                    hass.states.async_set(f"text.{DOMAIN}_produkt_name", "")
                    _LOGGER.info(
                        "Existing product '%s' added to shopping list", product_name
                    )
                    return True

                start_time = time.perf_counter()
                async with session.post(
                    ai_url, json={"name": product_name}, headers=headers
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"KI-Add-on Fehler: Status {resp.status}")

                    res_data = await resp.json()
                    duration = round(time.perf_counter() - start_time, 2)
                    product_attrs = res_data.get("product_data")
                    image_b64 = res_data.get("image_base64")

                _debug_log(
                    active_conf,
                    "AI response in %ss with attributes: %s",
                    duration,
                    product_attrs,
                )

                if _is_debug_enabled(active_conf):
                    hass.components.persistent_notification.create(
                        (
                            "### 🤖 KI Analyse Debug\n\n"
                            f"**Dauer:** {duration} Sekunden\n"
                            f"**Erkannte Daten:** `{product_attrs}`\n"
                            f"**Bild vorhanden:** {'✅ Ja' if image_b64 else '❌ Nein'}\n\n"
                            "*Import wurde aufgrund des Debug-Modus gestoppt.*"
                        ),
                        title="Grocy AI Assistant",
                        notification_id="grocy_ai_debug",
                    )
                    hass.states.async_set(
                        f"sensor.{DOMAIN}_response",
                        f"Debug fertig ({duration}s)",
                        {"icon": "mdi:flask"},
                    )
                    return True

                if not product_attrs:
                    raise Exception("KI lieferte keine validen Produktdaten.")

                grocy_url = f"{grocy_base_url}/objects/products"
                async with session.post(
                    grocy_url, json=product_attrs, headers=grocy_headers
                ) as g_resp:
                    if g_resp.status not in [200, 201]:
                        error_text = await g_resp.text()
                        raise Exception(f"Grocy API Fehler: {error_text}")

                    grocy_res_data = await g_resp.json()
                    new_id = grocy_res_data.get("created_object_id")

                image_status = "ohne Bild"
                if image_b64 and new_id:
                    try:
                        file_name = f"product_{new_id}.png"
                        img_bytes = base64.b64decode(image_b64)
                        upload_path_b64 = base64.b64encode(file_name.encode()).decode()
                        upload_url = (
                            f"{grocy_base_url}/files/productpictures/{upload_path_b64}"
                        )

                        img_resp = await session.put(
                            upload_url,
                            data=img_bytes,
                            headers={"GROCY-API-KEY": grocy_api_key},
                        )

                        if img_resp.status in [200, 201, 204]:
                            update_url = f"{grocy_base_url}/objects/products/{new_id}"
                            await session.put(
                                update_url,
                                json={"picture_file_name": file_name},
                                headers=grocy_headers,
                            )
                            image_status = "mit Bild"
                        else:
                            _debug_log(
                                active_conf,
                                "Image upload failed with status %s",
                                img_resp.status,
                            )
                    except Exception as img_err:
                        _LOGGER.error("Image upload failed: %s", img_err)

                shopping_url = f"{grocy_base_url}/stock/shoppinglist/add-product"
                shopping_payload = {"product_id": new_id, "amount": 1}
                async with session.post(
                    shopping_url, json=shopping_payload, headers=grocy_headers
                ) as shopping_resp:
                    if shopping_resp.status not in [200, 204]:
                        error_text = await shopping_resp.text()
                        raise Exception(
                            f"Shoppingliste konnte nicht aktualisiert werden: {error_text}"
                        )

                final_msg = f"Erfolg: {product_name} {image_status} erstellt + Einkaufsliste ({duration}s)"
                hass.states.async_set(
                    f"sensor.{DOMAIN}_response", final_msg, {"icon": "mdi:check-circle"}
                )
                hass.states.async_set(f"text.{DOMAIN}_produkt_name", "")
                _LOGGER.info(
                    "Successfully created '%s' and updated shopping list", product_name
                )

            except Exception as err:
                _LOGGER.error("Fehler im Ablauf: %s", err)
                hass.states.async_set(
                    f"sensor.{DOMAIN}_response",
                    f"Fehler nach {duration}s",
                    {"icon": "mdi:alert-circle"},
                )

    async def ask_ai_service(call):
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        if current_entry is None:
            _LOGGER.error("Config entry %s was not found", entry.entry_id)
            return

        active_conf = {**current_entry.data, **current_entry.options}
        api_key = active_conf.get(CONF_API_KEY)
        prompt = call.data.get("prompt", "Hallo")

        _debug_log(active_conf, "ask_ai called with prompt length %s", len(prompt))

        async with aiohttp.ClientSession() as session:
            try:
                url = "http://71139b3d-grocy-ai-assistant:8000/api/process"
                async with session.post(
                    url,
                    json={"prompt": prompt},
                    headers={"Authorization": f"Bearer {api_key}"},
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        hass.states.async_set(
                            f"sensor.{DOMAIN}_response",
                            result.get("answer", "Keine Antwort"),
                        )
                        _debug_log(active_conf, "ask_ai responded successfully")
                    else:
                        _LOGGER.warning("ask_ai returned status %s", resp.status)
            except Exception as err:
                _LOGGER.error("Fehler bei ask_ai: %s", err)

    hass.services.async_register(
        DOMAIN, "add_product_via_ai", add_product_via_ai_service
    )
    hass.services.async_register(DOMAIN, "ask_ai", ask_ai_service)
    _LOGGER.debug("Registered services for entry %s", entry.entry_id)

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "text"])
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    """Called when options are updated."""
    _LOGGER.info("Reloading config entry %s after options update", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor", "text"])
    """Unload the integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "text"]
    )
    _LOGGER.debug("Unload entry %s result: %s", entry.entry_id, unload_ok)
    return unload_ok
