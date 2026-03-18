from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ADDON_OPTIONS_YAML_PATH = Path("/data/options.yaml")
LEGACY_ADDON_OPTIONS_JSON_PATH = Path("/data/options.json")
REPOSITORY_OPTIONS_YAML_PATH = Path(__file__).resolve().parents[1] / "options.yaml"


def _parse_scalar(raw_value: str) -> Any:
    value = raw_value.strip()
    if not value:
        return ""

    if value.startswith(('"', "'")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                return value[1:-1]
            return value

    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        return value


def parse_simple_yaml(payload: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(
                f"Ungültige YAML-Zeile ohne Schlüssel/Wert-Trenner: {raw_line!r}"
            )
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Ungültige YAML-Zeile ohne Schlüssel: {raw_line!r}")
        data[key] = _parse_scalar(raw_value)
    return data


def _dump_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def dump_simple_yaml(data: dict[str, Any]) -> str:
    lines = [f"{key}: {_dump_scalar(value)}" for key, value in data.items()]
    return "\n".join(lines) + "\n"


def _load_yaml_options(path: Path) -> dict[str, Any]:
    payload = parse_simple_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} enthält kein Objekt")
    return payload


def load_addon_options() -> dict[str, Any]:
    if ADDON_OPTIONS_YAML_PATH.exists():
        return _load_yaml_options(ADDON_OPTIONS_YAML_PATH)

    if LEGACY_ADDON_OPTIONS_JSON_PATH.exists():
        payload = json.loads(LEGACY_ADDON_OPTIONS_JSON_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("options.json enthält kein Objekt")
        return payload

    if REPOSITORY_OPTIONS_YAML_PATH.exists():
        return _load_yaml_options(REPOSITORY_OPTIONS_YAML_PATH)

    return {}


def save_addon_options(data: dict[str, Any]) -> None:
    ADDON_OPTIONS_YAML_PATH.write_text(dump_simple_yaml(data), encoding="utf-8")
