from homeassistant import config_entries
import voluptuous as vol

# ... dein bestehender ConfigFlow ...

class GrocyAIConfigFlow(config_entries.ConfigFlow, domain="grocy_ai_assistant"):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # HIER muss die Erstellung stehen:
            return self.async_create_entry(
                title="Grocy AI Assistant", 
                data=user_input
            )

        # Wenn noch keine Daten da sind, zeige das Formular
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_key"): str,
                vol.Optional("ollama_url", default="http://172.17.0.1:11434/api/generate"): str,
            })
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return GrocyAIOptionsFlowHandler(config_entry)

class GrocyAIOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "api_key", 
                    default=self.config_entry.options.get(
                        "api_key", self.config_entry.data.get("api_key")
                    )
                ): str,
            }),
        )
        
