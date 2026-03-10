import logging

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.core import HomeAssistant

from .const import DEFAULT_ADDON_INGRESS_PATH

_LOGGER = logging.getLogger(__name__)


def _normalize_panel_url(url: str) -> str:
    """Normalize panel URLs for Home Assistant iframe usage."""
    normalized = (url or "").strip()
    if normalized.startswith("/api/hassio_ingress/") and not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


async def async_setup(hass: HomeAssistant, dashboard_url: str) -> None:
    """Register a custom dashboard panel."""
    resolved_url = _normalize_panel_url(dashboard_url)
    if dashboard_url.startswith("http://"):
        _LOGGER.warning(
            "Dashboard URL uses HTTP and would be blocked in HTTPS Home Assistant. Falling back to ingress path."
        )
        resolved_url = _normalize_panel_url(DEFAULT_ADDON_INGRESS_PATH)
    elif dashboard_url.startswith("http://localhost") or dashboard_url.startswith("https://localhost"):
        resolved_url = _normalize_panel_url(DEFAULT_ADDON_INGRESS_PATH)

    _LOGGER.debug("Registering panel with URL %s", resolved_url)
    async_register_built_in_panel(
        hass,
        "iframe",
        "Grocy AI",
        "mdi:brain",
        "grocy-ai",
        config={"url": resolved_url},
    )
