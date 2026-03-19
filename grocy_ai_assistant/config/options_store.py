from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ADDON_OPTIONS_YAML_PATH = Path("/data/options.yaml")
LEGACY_ADDON_OPTIONS_JSON_PATH = Path("/data/options.json")
REPOSITORY_CONFIG_YAML_PATH = Path(__file__).resolve().parents[1] / "config.yaml"

_TOP_LEVEL_OPTION_KEYS = (
    "api_key",
    "notification_global_enabled",
    "dashboard_polling_interval_seconds",
    "debug_mode",
)
_GROUPED_OPTION_KEYS = {
    "grocy": (
        "grocy_api_key",
        "grocy_base_url",
    ),
    "ollama": (
        "ollama_url",
        "ollama_model",
        "ollama_llava_model",
        "initial_info_sync",
    ),
    "scanner": (
        "scanner_barcode_fallback_seconds",
        "scanner_llava_min_confidence",
        "scanner_llava_timeout_seconds",
    ),
    "cloud_ai": (
        "image_generation_enabled",
        "openai_api_key",
        "openai_image_model",
        "generate_missing_product_images_on_startup",
    ),
}
_ALL_GROUPED_OPTION_KEYS = {
    option_key
    for option_keys in _GROUPED_OPTION_KEYS.values()
    for option_key in option_keys
}
_ALL_MAPPED_OPTION_KEYS = set(_TOP_LEVEL_OPTION_KEYS) | _ALL_GROUPED_OPTION_KEYS


def parse_simple_yaml(payload: str) -> dict[str, Any]:
    data = yaml.safe_load(payload) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML enthält kein Objekt")
    return data


def dump_simple_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    payload = parse_simple_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} enthält kein Objekt")
    return payload


def _extract_options_payload(payload: dict[str, Any]) -> dict[str, Any]:
    extracted_payload = payload
    while isinstance(extracted_payload.get("options"), dict):
        extracted_payload = extracted_payload["options"]
    return extracted_payload


def _collect_root_option_values(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for option_key in _TOP_LEVEL_OPTION_KEYS:
        if option_key in payload:
            normalized[option_key] = payload[option_key]

    for option_key in _ALL_GROUPED_OPTION_KEYS:
        if option_key in payload:
            normalized[option_key] = payload[option_key]

    for group_name, option_keys in _GROUPED_OPTION_KEYS.items():
        group_payload = payload.get(group_name)
        if not isinstance(group_payload, dict):
            continue
        for option_key in option_keys:
            if option_key in group_payload:
                normalized[option_key] = group_payload[option_key]

    return normalized


def _collect_nested_option_values(payload: Any) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if not isinstance(payload, dict):
        return normalized

    for value in payload.values():
        if not isinstance(value, dict):
            continue

        nested_root_values = _collect_root_option_values(value)
        for option_key, option_value in nested_root_values.items():
            normalized.setdefault(option_key, option_value)

        nested_values = _collect_nested_option_values(value)
        for option_key, option_value in nested_values.items():
            normalized.setdefault(option_key, option_value)

    return normalized


def _normalize_option_layout(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _extract_options_payload(payload)
    normalized = _collect_root_option_values(payload)

    nested_values = _collect_nested_option_values(payload)
    for option_key, option_value in nested_values.items():
        normalized.setdefault(option_key, option_value)

    for key, value in payload.items():
        if key in _ALL_MAPPED_OPTION_KEYS or key in _GROUPED_OPTION_KEYS:
            continue
        normalized[key] = value

    return normalized


def _nest_option_layout(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_option_layout(payload)
    nested: dict[str, Any] = {}

    for option_key in _TOP_LEVEL_OPTION_KEYS:
        if option_key in normalized:
            nested[option_key] = normalized[option_key]

    for key, value in normalized.items():
        if key not in _ALL_MAPPED_OPTION_KEYS:
            nested[key] = value

    for group_name, option_keys in _GROUPED_OPTION_KEYS.items():
        group_payload = {
            option_key: normalized[option_key]
            for option_key in option_keys
            if option_key in normalized
        }
        if group_payload:
            nested[group_name] = group_payload

    return nested


def _wrap_saved_options_if_needed(payload: dict[str, Any], nested_options: dict[str, Any]) -> dict[str, Any]:
    options_payload = payload.get("options")
    if isinstance(options_payload, dict):
        wrapped_payload = dict(payload)
        wrapped_payload["options"] = nested_options
        return wrapped_payload
    return nested_options


def load_addon_options() -> dict[str, Any]:
    if ADDON_OPTIONS_YAML_PATH.exists():
        return _normalize_option_layout(_load_yaml_file(ADDON_OPTIONS_YAML_PATH))

    if LEGACY_ADDON_OPTIONS_JSON_PATH.exists():
        payload = json.loads(LEGACY_ADDON_OPTIONS_JSON_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("options.json enthält kein Objekt")
        return payload

    if REPOSITORY_CONFIG_YAML_PATH.exists():
        payload = _load_yaml_file(REPOSITORY_CONFIG_YAML_PATH)
        options = payload.get("options", {})
        if not isinstance(options, dict):
            raise ValueError("config.yaml enthält kein Objekt unter 'options'")
        return _normalize_option_layout(options)

    return {}


def save_addon_options(data: dict[str, Any]) -> None:
    nested_options = _nest_option_layout(data)
    payload_to_write: dict[str, Any] = nested_options

    if ADDON_OPTIONS_YAML_PATH.exists():
        existing_payload = _load_yaml_file(ADDON_OPTIONS_YAML_PATH)
        payload_to_write = _wrap_saved_options_if_needed(
            existing_payload, nested_options
        )

    ADDON_OPTIONS_YAML_PATH.write_text(
        dump_simple_yaml(payload_to_write), encoding="utf-8"
    )
