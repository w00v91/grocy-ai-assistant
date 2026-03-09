async def async_setup(hass, dashboard_url: str):
    """Registriert ein eigenes Dashboard-Panel für die Produktsuche."""
    hass.components.frontend.async_register_built_in_panel(
        "iframe",
        "Grocy AI",
        "mdi:brain",
        "grocy-ai",
        {"url": dashboard_url},
    )
