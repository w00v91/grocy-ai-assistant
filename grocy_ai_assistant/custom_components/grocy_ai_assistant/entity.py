"""Shared Home Assistant entity helpers for the Grocy AI Assistant integration."""

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def build_device_info(entry_id: str) -> DeviceInfo:
    """Return the canonical device metadata for a config entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="Grocy AI Assistant",
        manufacturer="Eigene Integration",
    )
