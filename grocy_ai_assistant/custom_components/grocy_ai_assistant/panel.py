from urllib.parse import urlparse

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.core import HomeAssistant

from .const import DEFAULT_ADDON_INGRESS_PATH

def _normalize_panel_url(url: str) -> str:
    """Normalize panel URLs for Home Assistant iframe usage."""
    normalized = (url or "").strip()
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    ingress_index = normalized.find("/api/hassio_ingress/")
    if ingress_index != -1:
        normalized = normalized[ingress_index:]

    if normalized.startswith("/api/hassio_ingress/") and not normalized.endswith("/"):
        normalized = f"{normalized}/"

    parsed = urlparse(normalized)

    if parsed.scheme and parsed.netloc:
        return ""

    return normalized


async def async_setup(hass: HomeAssistant, dashboard_url: str) -> None:
    """Register a custom dashboard panel."""
    resolved_url = _normalize_panel_url(dashboard_url)
    if not resolved_url:
        resolved_url = _normalize_panel_url(DEFAULT_ADDON_INGRESS_PATH)

    async_register_built_in_panel(
        hass,
        "iframe",
        "Grocy AI",
        "mdi:brain",
        "grocy-ai",
        config={"url": resolved_url},
    )
