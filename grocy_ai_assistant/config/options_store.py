from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ADDON_OPTIONS_YAML_PATH = Path("/data/options.yaml")
LEGACY_ADDON_OPTIONS_JSON_PATH = Path("/data/options.json")
REPOSITORY_CONFIG_YAML_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


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


def _load_yaml_options(path: Path) -> dict[str, Any]:
    payload = parse_simple_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} enthält kein Objekt")
    return payload


def load_addon_options() -> dict[str, Any]:
    if ADDON_OPTIONS_YAML_PATH.exists():
        return _load_yaml_file(ADDON_OPTIONS_YAML_PATH)

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
        return options

    return {}


def save_addon_options(data: dict[str, Any]) -> None:
    ADDON_OPTIONS_YAML_PATH.write_text(dump_simple_yaml(data), encoding="utf-8")
