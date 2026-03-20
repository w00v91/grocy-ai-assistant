from pathlib import Path
from urllib.parse import urlparse

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.core import HomeAssistant

from .const import DEFAULT_ADDON_INGRESS_PATH

PANEL_TITLE = "Grocy AI"
PANEL_ICON = "mdi:brain"
PANEL_SLUG = "grocy-ai"
PANEL_WEBCOMPONENT = "grocy-ai-dashboard-panel"
PANEL_FRONTEND_URL_BASE = "/grocy_ai_assistant_panel"
PANEL_FRONTEND_MODULE = "grocy-ai-dashboard.js"


def _normalize_panel_url(url: str) -> str:
    """Normalize dashboard URLs for legacy dashboard links."""
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


def _frontend_directory() -> Path:
    """Return the directory that contains the native panel frontend bundle."""
    return Path(__file__).resolve().parent / "panel" / "frontend"


async def async_setup(hass: HomeAssistant, dashboard_url: str) -> None:
    """Register the Grocy AI dashboard as a native Home Assistant panel."""
    resolved_url = _normalize_panel_url(dashboard_url)
    if not resolved_url:
        resolved_url = _normalize_panel_url(DEFAULT_ADDON_INGRESS_PATH)

    frontend_directory = _frontend_directory()
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_FRONTEND_URL_BASE,
                str(frontend_directory),
                cache_headers=False,
            )
        ]
    )

    async_register_panel(
        hass,
        frontend_url_path=PANEL_SLUG,
        webcomponent_name=PANEL_WEBCOMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{PANEL_FRONTEND_URL_BASE}/{PANEL_FRONTEND_MODULE}",
        config={
            "legacy_dashboard_url": resolved_url,
            "frontend_base_url": PANEL_FRONTEND_URL_BASE,
        },
    )
