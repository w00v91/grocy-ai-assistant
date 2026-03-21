from pathlib import Path

from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.core import HomeAssistant

from .const import DEFAULT_ADDON_INGRESS_PATH, DOMAIN

PANEL_TITLE = "Grocy AI"
PANEL_ICON = "mdi:fridge-outline"
PANEL_SLUG = "grocy-ai"
PANEL_PATH = f"/{PANEL_SLUG}"
PANEL_WEBCOMPONENT = "grocy-ai-dashboard-panel"
PANEL_FRONTEND_URL_BASE = "/grocy_ai_assistant_panel"
PANEL_FRONTEND_MODULE = "grocy-ai-dashboard.js"
_PANEL_STATE_KEY = "_panel_state"


def _frontend_directory() -> Path:
    """Return the directory that contains the native panel frontend bundle."""
    return Path(__file__).resolve().parent / "panel" / "frontend"


async def async_setup(hass: HomeAssistant) -> None:
    """Register the Grocy AI dashboard as a native Home Assistant panel."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    panel_state = domain_data.setdefault(
        _PANEL_STATE_KEY,
        {"registrations": 0, "static_paths_registered": False},
    )

    resolved_url = DEFAULT_ADDON_INGRESS_PATH

    if not panel_state["static_paths_registered"]:
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
        panel_state["static_paths_registered"] = True

    panel_state["registrations"] += 1
    panel_state["legacy_dashboard_url"] = resolved_url

    async_remove_panel(hass, PANEL_SLUG)
    await async_register_panel(
        hass,
        frontend_url_path=PANEL_SLUG,
        webcomponent_name=PANEL_WEBCOMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{PANEL_FRONTEND_URL_BASE}/{PANEL_FRONTEND_MODULE}",
        config={
            "frontend_base_url": PANEL_FRONTEND_URL_BASE,
            "panel_path": PANEL_PATH,
            "panel_title": PANEL_TITLE,
            "panel_icon": PANEL_ICON,
            "legacy_dashboard_url": resolved_url,
            "page_title": PANEL_TITLE,
            "route": f"/{PANEL_SLUG}",
            "sidebar_icon": PANEL_ICON,
            "sidebar_title": PANEL_TITLE,
        },
    )


async def async_unload(hass: HomeAssistant) -> None:
    """Remove the Grocy AI dashboard panel when the last entry unloads."""
    domain_data = hass.data.get(DOMAIN, {})
    panel_state = domain_data.get(_PANEL_STATE_KEY)
    if not panel_state:
        return

    panel_state["registrations"] = max(0, panel_state["registrations"] - 1)
    if panel_state["registrations"] > 0:
        return

    async_remove_panel(hass, PANEL_SLUG)
    domain_data.pop(_PANEL_STATE_KEY, None)
