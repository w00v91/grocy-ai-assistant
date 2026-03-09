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
                vol.Required("api_key"): str,
                vol.Required("grocy_api_key"): str,
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

        # Holen der Daten mit Fallback auf leeres Dictionary
        # Das verhindert den 500er Fehler, falls noch keine Optionen da sind
        options = self.config_entry.options if self.config_entry.options else {}
        data = self.config_entry.data if self.config_entry.data else {}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("api_key", default=data.get("api_key", "")): str,
                vol.Required("grocy_api_key", default=data.get("grocy_api_key", "")): str,
                vol.Optional("debug_mode", default=options.get("debug_mode", False)): bool,
            }),
        )