from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from .const import DOMAIN

class GrocyAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Grocy AI Assistant", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_key"): str
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GrocyAIOptionsFlowHandler(config_entry)

class GrocyAIOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # WICHTIG: Sicherer Zugriff auf Daten
        # Wir nutzen .get() mit Fallback, falls ein Key fehlt
        data = self.config_entry.data or {}
        opts = self.config_entry.options or {}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("api_key", default=data.get("api_key", "")): str
            }),
        )