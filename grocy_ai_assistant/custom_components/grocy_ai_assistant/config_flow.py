import logging

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import (
    CONF_API_KEY,
    CONF_DASHBOARD_POLLING_INTERVAL_SECONDS,
    CONF_DEBUG_MODE,
    DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _safe_str(value, fallback: str = "") -> str:
    """Return a safe string value for config defaults."""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    return str(value)


def _safe_bool(value, fallback: bool = False) -> bool:
    """Return a safe boolean value for config defaults."""
    if value is None:
        return fallback
    return bool(value)


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
                    vol.Required(CONF_API_KEY): str,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GrocyAIOptionsFlowHandler(config_entry)


class GrocyAIOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._pending_options: dict = {}

    async def async_step_init(self, user_input=None):
        """General settings section."""
        if user_input is not None:
            self._pending_options.update(user_input)
            return await self.async_step_debug()

        options = self._config_entry.options or {}
        data = self._config_entry.data or {}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY,
                        default=_safe_str(
                            options.get(CONF_API_KEY, data.get(CONF_API_KEY)),
                        ),
                    ): str,
                    vol.Required(
                        CONF_DASHBOARD_POLLING_INTERVAL_SECONDS,
                        default=int(
                            options.get(
                                CONF_DASHBOARD_POLLING_INTERVAL_SECONDS,
                                data.get(
                                    CONF_DASHBOARD_POLLING_INTERVAL_SECONDS,
                                    DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS,
                                ),
                            )
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                }
            ),
        )

    async def async_step_debug(self, user_input=None):
        """Debug settings section shown after general options."""
        if user_input is not None:
            self._pending_options.update(user_input)
            _LOGGER.debug("Saving options with debug section values")
            return self.async_create_entry(title="", data=self._pending_options)

        options = self._config_entry.options or {}

        return self.async_show_form(
            step_id="debug",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEBUG_MODE,
                        default=_safe_bool(options.get(CONF_DEBUG_MODE), False),
                    ): bool,
                }
            ),
        )
