"""Constants for the Grocy AI Assistant integration."""

DOMAIN = "grocy_ai_assistant"
INTEGRATION_VERSION = "7.3.2"
DEFAULT_ADDON_INGRESS_PATH = "/api/hassio_ingress/grocy_ai_assistant/"
DEFAULT_ADDON_API_URL = "http://grocy_ai_assistant:8000"
DEFAULT_ADDON_PANEL_URL = DEFAULT_ADDON_INGRESS_PATH
DEFAULT_ADDON_BASE_URL = DEFAULT_ADDON_API_URL

CONF_API_KEY = "api_key"
CONF_API_BASE_URL = "api_base_url"
CONF_PANEL_URL = "panel_url"
CONF_GROCY_API_KEY = "grocy_api_key"
CONF_GROCY_BASE_URL = "grocy_base_url"
CONF_DEBUG_MODE = "debug_mode"
CONF_DASHBOARD_POLLING_INTERVAL_SECONDS = "dashboard_polling_interval_seconds"

DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS = 5

DEFAULT_GROCY_BASE_URL = "http://homeassistant.local:9192/api"
