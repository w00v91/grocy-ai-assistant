import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from . import panel as dashboard_panel
from .addon_client import AddonClient
from .const import (
    CONF_API_BASE_URL,
    DEFAULT_ADDON_BASE_URL,
    DOMAIN,
    INTEGRATION_VERSION,
)
from .entity_payloads import (
    build_analysis_status_payload,
    build_barcode_status_payload,
    build_error_status_payload,
    build_llava_status_payload,
)
from .services import (
    DATA_NOTIFICATION_MANAGER,
    NotificationManager,
    async_setup_notification_services,
)

_LOGGER = logging.getLogger(__name__)


def _get_entity_id(
    hass: HomeAssistant, entry_id: str, platform: str, unique_id: str, fallback: str
) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        platform, DOMAIN, f"{entry_id}_{unique_id}"
    )
    return entity_id or fallback


def _response_sensor_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "sensor",
        "response_text",
        f"sensor.{DOMAIN}_response",
    )


def _last_response_time_sensor_entity_id(
    hass: HomeAssistant, entry: ConfigEntry
) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "sensor",
        "ai_response_time_last_ms",
        f"sensor.{DOMAIN}_ki_antwortzeit_letzte_anfrage",
    )


def _average_response_time_sensor_entity_id(
    hass: HomeAssistant, entry: ConfigEntry
) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "sensor",
        "ai_response_time_avg_ms",
        f"sensor.{DOMAIN}_ki_antwortzeit_durchschnitt",
    )


def _product_input_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "text",
        "product_input",
        f"text.{DOMAIN}_produkt_name",
    )


def _analysis_status_sensor_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "sensor",
        "analysis_status",
        f"sensor.{DOMAIN}_analyse_status",
    )


def _barcode_status_sensor_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "sensor",
        "barcode_lookup_status",
        f"sensor.{DOMAIN}_barcode_scanner_status",
    )


def _llava_status_sensor_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    return _get_entity_id(
        hass,
        entry.entry_id,
        "sensor",
        "llava_scan_status",
        f"sensor.{DOMAIN}_llava_scanner_status",
    )


def _resolve_api_base_url(config: dict) -> str:
    return (
        config.get(CONF_API_BASE_URL)
        or config.get("addon_base_url")
        or DEFAULT_ADDON_BASE_URL
    )


def _migrate_entry_payload(payload: dict) -> dict:
    migrated = dict(payload)
    if CONF_API_BASE_URL not in migrated and migrated.get("addon_base_url"):
        migrated[CONF_API_BASE_URL] = migrated["addon_base_url"]
    migrated.pop("panel_url", None)
    return migrated


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration."""
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = _migrate_entry_payload(
        {**entry.data, **entry.options}
    )

    _LOGGER.info("Setting up Grocy AI Assistant for entry %s", entry.entry_id)

    await dashboard_panel.async_setup(hass)

    response_reset_unsubs = hass.data[DOMAIN].setdefault("_response_reset_unsubs", {})
    response_timing_stats = hass.data[DOMAIN].setdefault("_response_timing_stats", {})
    stats = response_timing_stats.setdefault(
        entry.entry_id,
        {"count": 0, "total_ms": 0.0},
    )

    def _cancel_response_reset() -> None:
        if unsubscribe := response_reset_unsubs.pop(entry.entry_id, None):
            unsubscribe()

    def _set_response_state(
        message: str,
        icon: str = "mdi:comment-text-outline",
        *,
        reset_after: bool = False,
    ) -> None:
        hass.states.async_set(
            _response_sensor_entity_id(hass, entry),
            message,
            {"icon": icon},
        )

        if reset_after:
            _cancel_response_reset()

            @callback
            def _reset_response_state(_now) -> None:
                response_reset_unsubs.pop(entry.entry_id, None)
                hass.states.async_set(
                    _response_sensor_entity_id(hass, entry),
                    "Bereit",
                    {"icon": "mdi:comment-text-outline"},
                )

            response_reset_unsubs[entry.entry_id] = async_call_later(
                hass, 30, _reset_response_state
            )
        else:
            _cancel_response_reset()

    def _set_response_timing_states(duration_ms: float) -> None:
        stats["count"] = int(stats.get("count", 0)) + 1
        stats["total_ms"] = float(stats.get("total_ms", 0.0)) + duration_ms
        average_ms = stats["total_ms"] / max(stats["count"], 1)

        hass.states.async_set(
            _last_response_time_sensor_entity_id(hass, entry),
            round(duration_ms, 1),
            {
                "unit_of_measurement": "ms",
                "state_class": "measurement",
                "requests_count": stats["count"],
            },
        )
        hass.states.async_set(
            _average_response_time_sensor_entity_id(hass, entry),
            round(average_ms, 1),
            {
                "unit_of_measurement": "ms",
                "state_class": "measurement",
                "requests_count": stats["count"],
            },
        )

    def _set_analysis_status(state: str, attributes: dict) -> None:
        hass.states.async_set(
            _analysis_status_sensor_entity_id(hass, entry),
            state,
            attributes,
        )

    def _set_barcode_status(state: str, attributes: dict) -> None:
        hass.states.async_set(
            _barcode_status_sensor_entity_id(hass, entry),
            state,
            attributes,
        )

    def _set_llava_status(state: str, attributes: dict) -> None:
        hass.states.async_set(
            _llava_status_sensor_entity_id(hass, entry),
            state,
            attributes,
        )

    def _build_active_client() -> AddonClient:
        current_entry = hass.config_entries.async_get_entry(entry.entry_id)
        if current_entry is None:
            raise RuntimeError(f"Config entry {entry.entry_id} wurde nicht gefunden")

        active_conf = {**current_entry.data, **current_entry.options}
        return AddonClient(
            _resolve_api_base_url(active_conf),
            active_conf.get("api_key", ""),
            integration_version=INTEGRATION_VERSION,
        )

    async def add_product_via_ai_service(call):
        """Analyze a product through the add-on and sync it to Grocy shopping list."""
        product_name = (call.data.get("name") or "").strip()

        if not product_name:
            state = hass.states.get(_product_input_entity_id(hass, entry))
            product_name = (state.state if state else "").strip()

        if not product_name:
            _set_response_state(
                "Kein Produktname übergeben", "mdi:alert-circle", reset_after=True
            )
            _set_analysis_status(
                *build_error_status_payload(
                    source="dashboard_search",
                    error="Kein Produktname übergeben",
                )
            )
            return

        client = _build_active_client()

        _set_response_state("KI analysiert…", "mdi:progress-clock")
        start_time = time.perf_counter()

        try:
            payload = await client.sync_product(product_name)
            duration_ms = (time.perf_counter() - start_time) * 1000
            _set_response_timing_states(duration_ms)
            if payload.get("_http_status") != 200:
                raise RuntimeError(payload.get("detail") or "Unbekannter API-Fehler")

            _set_analysis_status(
                *build_analysis_status_payload(
                    query=product_name,
                    payload=payload,
                    duration_ms=duration_ms,
                )
            )
            _set_response_state(
                payload.get("message", "Vorgang abgeschlossen"),
                "mdi:check-circle",
                reset_after=True,
            )
            hass.states.async_set(_product_input_entity_id(hass, entry), "")
        except Exception as error:
            _LOGGER.error("Fehler beim Add-on Aufruf: %s", error)
            _set_analysis_status(
                *build_error_status_payload(
                    source="dashboard_search",
                    error=error,
                    extra={"query": product_name},
                )
            )
            _set_response_state(
                f"Fehler: {error}", "mdi:alert-circle", reset_after=True
            )

    async def barcode_lookup_service(call):
        barcode = str(call.data.get("barcode") or "").strip()
        if not barcode:
            _set_barcode_status(
                *build_error_status_payload(
                    source="barcode_lookup",
                    error="Kein Barcode übergeben",
                )
            )
            return

        client = _build_active_client()
        start_time = time.perf_counter()
        try:
            payload = await client.lookup_barcode(barcode)
            duration_ms = (time.perf_counter() - start_time) * 1000
            if payload.get("_http_status") != 200:
                raise RuntimeError(
                    payload.get("detail") or "Barcode-Lookup fehlgeschlagen"
                )
            _set_barcode_status(
                *build_barcode_status_payload(
                    barcode=barcode,
                    payload=payload,
                    duration_ms=duration_ms,
                )
            )
        except Exception as error:
            _set_barcode_status(
                *build_error_status_payload(
                    source="barcode_lookup",
                    error=error,
                    extra={"barcode": barcode},
                )
            )

    async def scanner_llava_service(call):
        image_base64 = str(call.data.get("image_base64") or "").strip()
        if not image_base64:
            _set_llava_status(
                *build_error_status_payload(
                    source="scanner_llava",
                    error="Keine Bilddaten übergeben",
                )
            )
            return

        client = _build_active_client()
        start_time = time.perf_counter()
        try:
            payload = await client.scan_image(image_base64)
            duration_ms = (time.perf_counter() - start_time) * 1000
            if payload.get("_http_status") != 200:
                raise RuntimeError(payload.get("detail") or "LLaVA-Scan fehlgeschlagen")
            _set_llava_status(
                *build_llava_status_payload(
                    payload=payload,
                    duration_ms=duration_ms,
                )
            )
        except Exception as error:
            _set_llava_status(
                *build_error_status_payload(
                    source="scanner_llava",
                    error=error,
                )
            )

    hass.services.async_register(
        DOMAIN, "add_product_via_ai", add_product_via_ai_service
    )
    hass.services.async_register(DOMAIN, "sync_product", add_product_via_ai_service)
    hass.services.async_register(DOMAIN, "barcode_lookup", barcode_lookup_service)
    hass.services.async_register(DOMAIN, "scanner_llava_analyze", scanner_llava_service)
    hass.services.async_register(DOMAIN, "scan_image", scanner_llava_service)

    manager = NotificationManager(hass, entry.entry_id)
    await manager.async_initialize()
    hass.data[DOMAIN].setdefault(DATA_NOTIFICATION_MANAGER, {})[
        entry.entry_id
    ] = manager
    await async_setup_notification_services(hass, manager)

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "text", "button"]
    )
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry after options update."""
    _LOGGER.info("Reloading config entry %s after options update", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration entry."""
    if (
        unsubscribe := hass.data.get(DOMAIN, {})
        .get("_response_reset_unsubs", {})
        .pop(entry.entry_id, None)
    ):
        unsubscribe()

    hass.data.get(DOMAIN, {}).get("_response_timing_stats", {}).pop(
        entry.entry_id, None
    )

    hass.services.async_remove(DOMAIN, "add_product_via_ai")
    hass.services.async_remove(DOMAIN, "sync_product")
    hass.services.async_remove(DOMAIN, "barcode_lookup")
    hass.services.async_remove(DOMAIN, "scanner_llava_analyze")
    hass.services.async_remove(DOMAIN, "scan_image")
    hass.services.async_remove(DOMAIN, "notification_emit_event")
    hass.services.async_remove(DOMAIN, "notification_test_device")
    hass.services.async_remove(DOMAIN, "notification_test_all")
    hass.services.async_remove(DOMAIN, "notification_test_persistent")
    hass.data.get(DOMAIN, {}).get(DATA_NOTIFICATION_MANAGER, {}).pop(
        entry.entry_id, None
    )
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "text", "button"]
    )
    await dashboard_panel.async_unload(hass)
    _LOGGER.debug("Unload entry %s result: %s", entry.entry_id, unload_ok)
    return unload_ok
