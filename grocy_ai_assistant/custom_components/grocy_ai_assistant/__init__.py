
DOMAIN = "grocy_ai_assistant"

async def async_setup(hass, config):
    hass.data.setdefault(DOMAIN, {})
    return True
