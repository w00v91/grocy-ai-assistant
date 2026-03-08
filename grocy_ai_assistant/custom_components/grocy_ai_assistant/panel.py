
async def async_setup(hass):

    hass.components.frontend.async_register_built_in_panel(
        "iframe",
        "Grocy AI",
        "mdi:brain",
        "grocy-ai",
        {"url":"http://localhost:8000"}
    )
