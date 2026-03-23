import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from . import panel as dashboard_panel
from .addon_client import AddonClient
from .const import (
    CONF_API_BASE_URL,
    DEFAULT_ADDON_BASE_URL,
    DOMAIN,
    INTEGRATION_VERSION,
)
from .coordinator import DATA_ENTRY_CONFIG, async_setup_entry_coordinators
from .entity_payloads import (
    build_analysis_status_payload,
    build_barcode_status_payload,
    build_error_status_payload,
    build_llava_status_payload,
)
from .runtime import (
    DATA_ENTRY_RUNTIME,
    RUNTIME_ANALYSIS_STATUS,
    RUNTIME_BARCODE_STATUS,
    RUNTIME_LLAVA_STATUS,
    RUNTIME_RESPONSE,
    RUNTIME_RESPONSE_TIME_AVG,
    RUNTIME_RESPONSE_TIME_LAST,
    async_set_runtime_sensor_payload,
    build_default_entry_runtime,
    get_entry_runtime_data,
    get_product_input_value,
)
from .text import async_set_product_input_value
from .services import (
    DATA_NOTIFICATION_MANAGER,
    NotificationManager,
    async_setup_notification_services,
)

_LOGGER = logging.getLogger(__name__)


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
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ENTRY_CONFIG: _migrate_entry_payload({**entry.data, **entry.options}),
        DATA_ENTRY_RUNTIME: build_default_entry_runtime(),
    }

    _LOGGER.info("Setting up Grocy AI Assistant for entry %s", entry.entry_id)

    await async_setup_entry_coordinators(hass, entry)
    await dashboard_panel.async_setup(hass)

    entry_runtime = get_entry_runtime_data(hass, entry.entry_id)

    def _cancel_response_reset() -> None:
        if unsubscribe := entry_runtime.pop("response_reset_unsub", None):
            unsubscribe()

    def _set_response_state(
        message: str,
        icon: str = "mdi:comment-text-outline",
        *,
        reset_after: bool = False,
    ) -> None:
        async_set_runtime_sensor_payload(
            hass,
            entry.entry_id,
            RUNTIME_RESPONSE,
            state=message,
            attributes={},
            icon=icon,
        )

        if reset_after:
            _cancel_response_reset()

            @callback
            def _reset_response_state(_now) -> None:
                entry_runtime.pop("response_reset_unsub", None)
                async_set_runtime_sensor_payload(
                    hass,
                    entry.entry_id,
                    RUNTIME_RESPONSE,
                    state="Bereit",
                    attributes={},
                    icon="mdi:comment-text-outline",
                )

            entry_runtime["response_reset_unsub"] = async_call_later(
                hass, 30, _reset_response_state
            )
        else:
            _cancel_response_reset()

    def _set_response_timing_states(duration_ms: float) -> None:
        stats = entry_runtime.setdefault(
            "response_timing_stats",
            {"count": 0, "total_ms": 0.0},
        )
        stats["count"] = int(stats.get("count", 0)) + 1
        stats["total_ms"] = float(stats.get("total_ms", 0.0)) + duration_ms
        average_ms = stats["total_ms"] / max(stats["count"], 1)
        shared_attributes = {"requests_count": stats["count"]}

        async_set_runtime_sensor_payload(
            hass,
            entry.entry_id,
            RUNTIME_RESPONSE_TIME_LAST,
            state=round(duration_ms, 1),
            attributes=shared_attributes,
        )
        async_set_runtime_sensor_payload(
            hass,
            entry.entry_id,
            RUNTIME_RESPONSE_TIME_AVG,
            state=round(average_ms, 1),
            attributes=shared_attributes,
        )

    def _set_analysis_status(state: str, attributes: dict) -> None:
        async_set_runtime_sensor_payload(
            hass,
            entry.entry_id,
            RUNTIME_ANALYSIS_STATUS,
            state=state,
            attributes=attributes,
        )

    def _set_barcode_status(state: str, attributes: dict) -> None:
        async_set_runtime_sensor_payload(
            hass,
            entry.entry_id,
            RUNTIME_BARCODE_STATUS,
            state=state,
            attributes=attributes,
        )

    def _set_llava_status(state: str, attributes: dict) -> None:
        async_set_runtime_sensor_payload(
            hass,
            entry.entry_id,
            RUNTIME_LLAVA_STATUS,
            state=state,
            attributes=attributes,
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
            product_name = get_product_input_value(hass, entry.entry_id).strip()

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
            async_set_product_input_value(hass, entry.entry_id, "")
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
    runtime = (
        hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get(DATA_ENTRY_RUNTIME, {})
    )
    if unsubscribe := runtime.pop("response_reset_unsub", None):
        unsubscribe()

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
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    await dashboard_panel.async_unload(hass)
    _LOGGER.debug("Unload entry %s result: %s", entry.entry_id, unload_ok)
    return unload_ok
