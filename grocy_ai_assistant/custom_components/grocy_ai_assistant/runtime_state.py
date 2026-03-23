"""Entry-scoped runtime state and dispatcher helpers for Home Assistant entities."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN

DATA_ENTRY_RUNTIME_STATE = "runtime_state"

RUNTIME_RESPONSE = "response"
RUNTIME_RESPONSE_TIMING = "response_timing"
RUNTIME_ANALYSIS_STATUS = "analysis_status"
RUNTIME_BARCODE_STATUS = "barcode_status"
RUNTIME_LLAVA_STATUS = "llava_status"
RUNTIME_PRODUCT_INPUT = "product_input"

DEFAULT_RESPONSE_PAYLOAD: dict[str, Any] = {
    "state": "ready",
    "attributes": {"icon": "mdi:comment-text-outline"},
}
DEFAULT_STATUS_PAYLOAD: dict[str, Any] = {"state": "ready", "attributes": {}}
DEFAULT_RESPONSE_TIMING: dict[str, Any] = {
    "count": 0,
    "total_ms": 0.0,
    "last_ms": None,
    "average_ms": None,
}


def _runtime_defaults() -> dict[str, Any]:
    return {
        RUNTIME_RESPONSE: deepcopy(DEFAULT_RESPONSE_PAYLOAD),
        RUNTIME_RESPONSE_TIMING: deepcopy(DEFAULT_RESPONSE_TIMING),
        RUNTIME_ANALYSIS_STATUS: deepcopy(DEFAULT_STATUS_PAYLOAD),
        RUNTIME_BARCODE_STATUS: deepcopy(DEFAULT_STATUS_PAYLOAD),
        RUNTIME_LLAVA_STATUS: deepcopy(DEFAULT_STATUS_PAYLOAD),
        RUNTIME_PRODUCT_INPUT: "",
    }


def ensure_entry_runtime_data(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    entry_runtime = domain_data.setdefault(entry_id, {})
    return entry_runtime


def ensure_entry_runtime_state(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    entry_runtime = ensure_entry_runtime_data(hass, entry_id)
    runtime_state = entry_runtime.setdefault(
        DATA_ENTRY_RUNTIME_STATE, _runtime_defaults()
    )

    for key, default_value in _runtime_defaults().items():
        runtime_state.setdefault(key, deepcopy(default_value))

    return runtime_state


def get_entry_runtime_state(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    entry_runtime = ensure_entry_runtime_data(hass, entry_id)
    runtime_state = entry_runtime.get(DATA_ENTRY_RUNTIME_STATE)
    if not isinstance(runtime_state, dict):
        runtime_state = _runtime_defaults()
        entry_runtime[DATA_ENTRY_RUNTIME_STATE] = runtime_state
    return runtime_state


def dispatcher_signal(entry_id: str, key: str) -> str:
    return f"{DOMAIN}_{entry_id}_{key}_updated"


def get_runtime_payload(hass: HomeAssistant, entry_id: str, key: str) -> dict[str, Any]:
    runtime_state = ensure_entry_runtime_state(hass, entry_id)
    payload = runtime_state.get(key)
    return deepcopy(payload) if isinstance(payload, dict) else {}


def async_set_runtime_payload(
    hass: HomeAssistant,
    entry_id: str,
    key: str,
    *,
    state: Any,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_state = ensure_entry_runtime_state(hass, entry_id)
    payload = {
        "state": state,
        "attributes": dict(attributes or {}),
    }
    runtime_state[key] = payload
    async_dispatcher_send(hass, dispatcher_signal(entry_id, key), deepcopy(payload))
    return deepcopy(payload)


def get_response_timing(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    runtime_state = ensure_entry_runtime_state(hass, entry_id)
    timing = runtime_state.get(RUNTIME_RESPONSE_TIMING)
    return (
        deepcopy(timing)
        if isinstance(timing, dict)
        else deepcopy(DEFAULT_RESPONSE_TIMING)
    )


def async_record_response_timing(
    hass: HomeAssistant, entry_id: str, duration_ms: float
) -> dict[str, Any]:
    runtime_state = ensure_entry_runtime_state(hass, entry_id)
    timing = runtime_state.setdefault(
        RUNTIME_RESPONSE_TIMING, deepcopy(DEFAULT_RESPONSE_TIMING)
    )

    count = int(timing.get("count", 0)) + 1
    total_ms = float(timing.get("total_ms", 0.0)) + float(duration_ms)
    average_ms = total_ms / max(count, 1)

    updated = {
        "count": count,
        "total_ms": total_ms,
        "last_ms": round(float(duration_ms), 1),
        "average_ms": round(average_ms, 1),
    }
    runtime_state[RUNTIME_RESPONSE_TIMING] = updated
    async_dispatcher_send(
        hass,
        dispatcher_signal(entry_id, RUNTIME_RESPONSE_TIMING),
        deepcopy(updated),
    )
    return deepcopy(updated)


def get_product_input_value(hass: HomeAssistant, entry_id: str) -> str:
    runtime_state = ensure_entry_runtime_state(hass, entry_id)
    return str(runtime_state.get(RUNTIME_PRODUCT_INPUT) or "")


def async_set_product_input_value(
    hass: HomeAssistant, entry_id: str, value: str
) -> str:
    normalized = str(value)
    runtime_state = ensure_entry_runtime_state(hass, entry_id)
    runtime_state[RUNTIME_PRODUCT_INPUT] = normalized
    async_dispatcher_send(
        hass,
        dispatcher_signal(entry_id, RUNTIME_PRODUCT_INPUT),
        normalized,
    )
    return normalized
