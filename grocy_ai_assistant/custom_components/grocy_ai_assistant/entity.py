"""Shared Home Assistant entity helpers for the Grocy AI Assistant integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def _get_status_attributes(hass: Any, entry_id: str) -> dict[str, Any]:
    entry_data = (
        ((hass or {}).data or {}).get(DOMAIN, {}).get(entry_id, {})
        if hass is not None
        else {}
    )
    coordinators = entry_data.get("coordinators", {})
    status_coordinator = coordinators.get("status", {})
    coordinator_data = getattr(status_coordinator, "data", {}) or {}
    status_payload = coordinator_data.get("status", {})
    attributes = status_payload.get("attributes", {})
    return attributes if isinstance(attributes, dict) else {}


def _get_configuration_url(hass: Any, entry_id: str) -> str | None:
    entry_data = (
        ((hass or {}).data or {}).get(DOMAIN, {}).get(entry_id, {})
        if hass is not None
        else {}
    )
    config = entry_data.get("config", {})
    if not isinstance(config, dict):
        return None
    api_base_url = str(
        config.get("api_base_url") or config.get("addon_base_url") or ""
    ).strip()
    return api_base_url or None


def build_device_info(entry_id: str, hass: Any | None = None) -> DeviceInfo:
    """Return the canonical device metadata for a config entry."""
    status_attributes = _get_status_attributes(hass, entry_id)
    addon_version = str(status_attributes.get("addon_version", "")).strip()

    payload: dict[str, Any] = {
        "identifiers": {(DOMAIN, entry_id)},
        "name": "Grocy AI Assistant Add-on",
        "manufacturer": "Grocy AI Assistant",
        "model": "Grocy AI Assistant Add-on",
        "model_id": "grocy_ai_assistant_addon",
    }
    if addon_version:
        payload["sw_version"] = addon_version
    if configuration_url := _get_configuration_url(hass, entry_id):
        payload["configuration_url"] = configuration_url
    return DeviceInfo(
        **payload
    )
