
import voluptuous as vol
from homeassistant import config_entries

DOMAIN = "grocy_ai_assistant"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input=None):

        if user_input is not None:

            return self.async_create_entry(
                title="Grocy AI Assistant",
                data=user_input
            )

        schema = vol.Schema({
            vol.Required("api_url"): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema
        )
