"""Utilities for redacting sensitive data structures."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "token",
    "access_token",
    "refresh_token",
}

_MASK = "***"


def redact_sensitive_data(value: Any) -> Any:
    """Recursively mask sensitive keys in nested dict/list structures."""
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            key_name = str(key)
            if normalized_key in SENSITIVE_KEYS:
                redacted[key_name] = _MASK
                continue
            if normalized_key in {"headers", "_headers"} and isinstance(item, Mapping):
                redacted[key_name] = {
                    str(header_key): _MASK
                    for header_key in item.keys()
                }
                continue
            redacted[key_name] = redact_sensitive_data(item)
        return redacted

    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)

    return value
