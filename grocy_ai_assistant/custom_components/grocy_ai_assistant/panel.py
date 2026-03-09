import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, dashboard_url: str):
    """Register a custom dashboard panel."""
    _LOGGER.debug("Registering panel with URL %s", dashboard_url)
    hass.components.frontend.async_register_built_in_panel(
        "iframe",
        "Grocy AI",
        "mdi:brain",
        "grocy-ai",
        {"url": dashboard_url},
    )
