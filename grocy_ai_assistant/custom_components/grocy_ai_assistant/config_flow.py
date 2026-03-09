import logging

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import DEFAULT_ADDON_BASE_URL, DOMAIN
from .const import (
    CONF_API_KEY,
    CONF_DEBUG_MODE,
    CONF_GROCY_API_KEY,
    CONF_GROCY_BASE_URL,
    DEFAULT_GROCY_BASE_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class GrocyAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            _LOGGER.debug("Creating config entry from user step")
            return self.async_create_entry(title="Grocy AI Assistant", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("api_key"): str,
                    vol.Required("addon_base_url", default=DEFAULT_ADDON_BASE_URL): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_GROCY_API_KEY): str,
                    vol.Optional(
                        CONF_GROCY_BASE_URL, default=DEFAULT_GROCY_BASE_URL
                    ): str,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GrocyAIOptionsFlowHandler(config_entry)


class GrocyAIOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self._pending_options: dict = {}

    async def async_step_init(self, user_input=None):
        """General settings section."""
        if user_input is not None:
            self._pending_options.update(user_input)
            return await self.async_step_debug()

        options = self.config_entry.options or {}
        data = self.config_entry.data or {}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "api_key",
                        default=options.get("api_key", data.get("api_key", "")),
                    ): str,
                    vol.Required(
                        "addon_base_url",
                        default=options.get(
                            "addon_base_url",
                            data.get("addon_base_url", DEFAULT_ADDON_BASE_URL),
                        ),
                    ): str,
                        CONF_API_KEY,
                        default=options.get(CONF_API_KEY, data.get(CONF_API_KEY, "")),
                    ): str,
                    vol.Required(
                        CONF_GROCY_API_KEY,
                        default=options.get(
                            CONF_GROCY_API_KEY, data.get(CONF_GROCY_API_KEY, "")
                        ),
                    ): str,
                    vol.Required(
                        CONF_GROCY_BASE_URL,
                        default=options.get(
                            CONF_GROCY_BASE_URL,
                            data.get(CONF_GROCY_BASE_URL, DEFAULT_GROCY_BASE_URL),
                        ),
                    ): str,
                }
            ),
        )

    async def async_step_debug(self, user_input=None):
        """Debug settings section shown after general options."""
        if user_input is not None:
            self._pending_options.update(user_input)
            _LOGGER.debug("Saving options with debug section values")
            return self.async_create_entry(title="", data=self._pending_options)

        options = self.config_entry.options if self.config_entry.options else {}

        return self.async_show_form(
            step_id="debug",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEBUG_MODE,
                        default=options.get(CONF_DEBUG_MODE, False),
                    ): bool,
                }
            ),
        )
