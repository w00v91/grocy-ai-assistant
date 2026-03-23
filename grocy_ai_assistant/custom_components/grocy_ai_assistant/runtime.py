"""Runtime state helpers for entity-driven updates in the HA integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN

DATA_ENTRY_RUNTIME = "entity_runtime"

RUNTIME_RESPONSE = "response"
RUNTIME_RESPONSE_TIME_LAST = "response_time_last"
RUNTIME_RESPONSE_TIME_AVG = "response_time_avg"
RUNTIME_ANALYSIS_STATUS = "analysis_status"
RUNTIME_BARCODE_STATUS = "barcode_status"
RUNTIME_LLAVA_STATUS = "llava_status"
RUNTIME_PRODUCT_INPUT = "product_input"


RuntimePayload = dict[str, Any]


def build_default_entry_runtime() -> RuntimePayload:
    """Return the default entity runtime payload for a config entry."""
    return {
        RUNTIME_RESPONSE: {
            "state": "Bereit",
            "icon": "mdi:comment-text-outline",
            "attributes": {},
        },
        RUNTIME_RESPONSE_TIME_LAST: {
            "state": None,
            "attributes": {"requests_count": 0},
        },
        RUNTIME_RESPONSE_TIME_AVG: {
            "state": None,
            "attributes": {"requests_count": 0},
        },
        RUNTIME_ANALYSIS_STATUS: {"state": "Bereit", "attributes": {}},
        RUNTIME_BARCODE_STATUS: {"state": "Bereit", "attributes": {}},
        RUNTIME_LLAVA_STATUS: {"state": "Bereit", "attributes": {}},
        RUNTIME_PRODUCT_INPUT: {"value": ""},
        "response_timing_stats": {"count": 0, "total_ms": 0.0},
    }


def get_entry_data(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    """Return the entry-scoped runtime container stored in ``hass.data``."""
    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(entry_id)
    if not isinstance(entry_data, dict):
        raise KeyError(f"Keine Runtime-Daten für Entry {entry_id} gefunden")
    return entry_data


def get_entry_runtime_data(hass: HomeAssistant, entry_id: str) -> RuntimePayload:
    """Return the entity runtime payload for a config entry."""
    runtime = get_entry_data(hass, entry_id).setdefault(
        DATA_ENTRY_RUNTIME,
        build_default_entry_runtime(),
    )
    if not isinstance(runtime, dict):
        raise KeyError(f"Keine Entity-Runtime für Entry {entry_id} gefunden")
    return runtime


def async_runtime_signal(entry_id: str, key: str) -> str:
    """Build the dispatcher signal for a runtime payload key."""
    return f"{DOMAIN}_runtime_{entry_id}_{key}"


def async_set_runtime_sensor_payload(
    hass: HomeAssistant,
    entry_id: str,
    key: str,
    *,
    state: Any,
    attributes: dict[str, Any] | None = None,
    icon: str | None = None,
) -> None:
    """Store a sensor payload in runtime data and notify subscribed entities."""
    payload = {
        "state": state,
        "attributes": dict(attributes or {}),
    }
    if icon is not None:
        payload["icon"] = icon

    get_entry_runtime_data(hass, entry_id)[key] = payload
    async_dispatcher_send(hass, async_runtime_signal(entry_id, key))


def get_runtime_sensor_payload(
    hass: HomeAssistant,
    entry_id: str,
    key: str,
) -> dict[str, Any]:
    """Return the current runtime sensor payload for an entry/key pair."""
    payload = get_entry_runtime_data(hass, entry_id).get(key)
    return dict(payload) if isinstance(payload, dict) else {}


def set_product_input_value(
    hass: HomeAssistant,
    entry_id: str,
    value: str,
) -> None:
    """Persist the product input value in runtime state."""
    get_entry_runtime_data(hass, entry_id)[RUNTIME_PRODUCT_INPUT] = {
        "value": str(value),
    }


def get_product_input_value(hass: HomeAssistant, entry_id: str) -> str:
    """Return the current product input value from runtime state."""
    payload = get_entry_runtime_data(hass, entry_id).get(RUNTIME_PRODUCT_INPUT)
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("value") or "")
