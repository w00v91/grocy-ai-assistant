"""Diagnostics support for the Grocy AI Assistant integration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import (
    COORDINATOR_INVENTORY,
    COORDINATOR_RECIPE_SUGGESTIONS,
    COORDINATOR_STATUS,
    DATA_COORDINATORS,
)
from .runtime_state import DATA_ENTRY_RUNTIME_STATE

_REDACT_EXACT_KEYS = {
    "api_key",
    "authorization",
    "x-api-key",
    "access_token",
    "refresh_token",
    "token",
    "bearer",
    "headers",
}
_REDACT_PARTIAL_KEYS = (
    "token",
    "secret",
    "password",
    "authorization",
    "header",
    "cookie",
    "apikey",
    "api_key",
)
_REDACTED = "***REDACTED***"


def _is_sensitive_key(key: Any) -> bool:
    key_str = str(key).strip().lower()
    if key_str in _REDACT_EXACT_KEYS:
        return True
    return any(part in key_str for part in _REDACT_PARTIAL_KEYS)


def _to_serializable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Exception):
        return f"{value.__class__.__name__}: {value}"

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Mapping):
        return {
            str(key): _to_serializable(item_value) for key, item_value in value.items()
        }

    if isinstance(value, (list, tuple, set, frozenset)):
        return [_to_serializable(item) for item in value]

    if hasattr(value, "as_dict") and callable(value.as_dict):
        try:
            return _to_serializable(value.as_dict())
        except Exception:  # pragma: no cover - defensive fallback
            return str(value)

    return str(value)


def _redact_sensitive(data: dict) -> dict:
    """Return a redacted and serializable diagnostics dictionary."""

    redacted: dict[str, Any] = {}
    for key, value in data.items():
        str_key = str(key)
        if _is_sensitive_key(str_key):
            redacted[str_key] = _REDACTED
            continue

        serializable = _to_serializable(value)
        if isinstance(serializable, dict):
            redacted[str_key] = _redact_sensitive(serializable)
        elif isinstance(serializable, list):
            redacted[str_key] = [
                _redact_sensitive(item) if isinstance(item, dict) else item
                for item in serializable
            ]
        else:
            redacted[str_key] = serializable
    return redacted


def _coordinator_diagnostics(coordinator: Any) -> dict[str, Any]:
    if coordinator is None:
        return {}

    raw_data = _to_serializable(getattr(coordinator, "data", {}))
    if not isinstance(raw_data, dict):
        raw_data = {"value": raw_data}

    return {
        "last_update_success": bool(getattr(coordinator, "last_update_success", False)),
        "last_exception": _to_serializable(getattr(coordinator, "last_exception", None)),
        "data": _redact_sensitive(raw_data),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    domain_data = hass.data.get(DOMAIN, {})
    entry_runtime = domain_data.get(entry.entry_id, {})

    coordinators = {}
    raw_coordinators = entry_runtime.get(DATA_COORDINATORS)
    if isinstance(raw_coordinators, dict):
        coordinators = {
            COORDINATOR_STATUS: _coordinator_diagnostics(
                raw_coordinators.get(COORDINATOR_STATUS)
            ),
            COORDINATOR_INVENTORY: _coordinator_diagnostics(
                raw_coordinators.get(COORDINATOR_INVENTORY)
            ),
            COORDINATOR_RECIPE_SUGGESTIONS: _coordinator_diagnostics(
                raw_coordinators.get(COORDINATOR_RECIPE_SUGGESTIONS)
            ),
        }

    runtime_state = entry_runtime.get(DATA_ENTRY_RUNTIME_STATE, {})

    return {
        "entry": {
            "data": _redact_sensitive(_to_serializable(dict(entry.data))),
            "options": _redact_sensitive(_to_serializable(dict(entry.options))),
        },
        "coordinators": coordinators,
        "runtime_state": _redact_sensitive(
            _to_serializable(runtime_state if isinstance(runtime_state, dict) else {})
        ),
        "runtime_data": _redact_sensitive(
            _to_serializable(entry_runtime if isinstance(entry_runtime, dict) else {})
        ),
    }
