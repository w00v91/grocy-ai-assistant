import logging

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, dashboard_url: str) -> None:
    """Register a custom dashboard panel."""
    _LOGGER.debug("Registering panel with URL %s", dashboard_url)
    async_register_built_in_panel(
        hass,
        "iframe",
        "Grocy AI",
        "mdi:brain",
        "grocy-ai",
        config={"url": dashboard_url},
    )
