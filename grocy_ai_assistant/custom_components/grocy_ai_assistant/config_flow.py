from homeassistant import config_entries
from homeassistant.core import callback  # <-- WICHTIG: Dieser Import hat gefehlt
import voluptuous as vol
from .const import DOMAIN

class GrocyAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurations-Flow für den Grocy AI Assistant."""
    
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Erster Schritt bei der Installation."""
        if user_input is not None:
            return self.async_create_entry(
                title="Grocy AI Assistant", 
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_key"): str,
                vol.Required("grocy_api_key"): str,
                vol.Optional("ollama_url", default="http://172.17.0.1:11434/api/generate"): str,
                vol.Optional("sd_api_url", default="http://172.17.0.1:7860/sdapi/v1/txt2img"): str,
                vol.Optional("debug_mode", default=False): bool, # <-- Neuer Debug Schalter
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

        # Merge von data und options, damit immer die aktuellsten Werte geladen werden
        current_config = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("api_key", default=current_config.get("api_key", "")): str,
                vol.Required("grocy_api_key", default=current_config.get("grocy_api_key", "")): str,
                vol.Optional("ollama_url", default=current_config.get("ollama_url", "")): str,
                vol.Optional("sd_api_url", default=current_config.get("sd_api_url", "")): str,
                vol.Optional("debug_mode", default=current_config.get("debug_mode", False)): bool,
            }),
        )