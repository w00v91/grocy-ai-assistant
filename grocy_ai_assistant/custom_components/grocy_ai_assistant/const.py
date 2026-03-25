"""Constants for the Grocy AI Assistant integration."""

DOMAIN = "grocy_ai_assistant"
INTEGRATION_VERSION = "8.0.36"
DEFAULT_ADDON_INGRESS_PATH = "/api/hassio_ingress/grocy_ai_assistant/"
DEFAULT_ADDON_API_URL = "http://local-grocy-ai-assistant:8000"
DEFAULT_ADDON_BASE_URL = DEFAULT_ADDON_API_URL

CONF_API_KEY = "api_key"
CONF_API_BASE_URL = "api_base_url"
CONF_DEBUG_MODE = "debug_mode"
CONF_DASHBOARD_POLLING_INTERVAL_SECONDS = "dashboard_polling_interval_seconds"

DASHBOARD_POLLING_DISABLED_INTERVAL_SECONDS = 0
DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS = 5
