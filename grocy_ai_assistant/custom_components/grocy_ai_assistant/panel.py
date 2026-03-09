import logging

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.core import HomeAssistant

from .const import DEFAULT_ADDON_INGRESS_PATH

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, dashboard_url: str) -> None:
    """Register a custom dashboard panel."""
    resolved_url = dashboard_url
    if dashboard_url.startswith("http://localhost") or dashboard_url.startswith("https://localhost"):
        resolved_url = DEFAULT_ADDON_INGRESS_PATH

    _LOGGER.debug("Registering panel with URL %s", resolved_url)
    async_register_built_in_panel(
        hass,
        "iframe",
        "Grocy AI",
        "mdi:brain",
        "grocy-ai",
        config={"url": resolved_url},
    )
