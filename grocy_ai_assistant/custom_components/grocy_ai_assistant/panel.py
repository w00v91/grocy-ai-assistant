from aiohttp import web
from pathlib import Path

from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.core import HomeAssistant

from .addon_client import AddonClient
from .const import (
    CONF_API_BASE_URL,
    CONF_DASHBOARD_POLLING_INTERVAL_SECONDS,
    DEFAULT_ADDON_BASE_URL,
    DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS,
    DOMAIN,
    INTEGRATION_VERSION,
)

PANEL_TITLE = "Grocy AI"
PANEL_ICON = "mdi:fridge-outline"
PANEL_SLUG = "grocy-ai"
PANEL_PATH = f"/{PANEL_SLUG}"
PANEL_WEBCOMPONENT = "grocy-ai-dashboard-panel"
PANEL_FRONTEND_URL_BASE = "/grocy_ai_assistant_panel"
PANEL_FRONTEND_MODULE = "grocy-ai-dashboard.js"
PANEL_PROXY_URL_BASE = "/api/grocy_ai_assistant/dashboard-proxy"
PANEL_PICTURE_PROXY_URL = f"{PANEL_PROXY_URL_BASE}/api/dashboard/product-picture"
_PANEL_STATE_KEY = "_panel_state"


def _frontend_directory() -> Path:
    """Return the directory that contains the native panel frontend bundle."""
    return Path(__file__).resolve().parent / "panel" / "frontend"


def _resolve_api_base_url(config: dict) -> str:
    return (
        config.get(CONF_API_BASE_URL)
        or config.get("addon_base_url")
        or DEFAULT_ADDON_BASE_URL
    )


def _resolve_entry_config(entry_value: dict) -> dict:
    if not isinstance(entry_value, dict):
        return {}
    nested_config = entry_value.get("config")
    if isinstance(nested_config, dict):
        return nested_config
    return entry_value


def _resolve_active_config(hass: HomeAssistant) -> dict:
    domain_data = hass.data.get(DOMAIN, {})
    for key, value in domain_data.items():
        if key.startswith("_") or key == _PANEL_STATE_KEY:
            continue
        if isinstance(value, dict):
            return _resolve_entry_config(value)
    return {}


def _build_active_client(hass: HomeAssistant) -> AddonClient:
    active_config = _resolve_active_config(hass)
    return AddonClient(
        _resolve_api_base_url(active_config),
        active_config.get("api_key", ""),
        integration_version=INTEGRATION_VERSION,
    )


async def _proxy_dashboard_request(
    hass: HomeAssistant, request, path: str = ""
) -> web.Response:
    client = _build_active_client(hass)
    request_path = f"/{path}" if path and not path.startswith("/") else (path or "/")
    proxy_headers = {
        "X-Ingress-Path": PANEL_PROXY_URL_BASE,
        "X-Forwarded-Prefix": PANEL_PROXY_URL_BASE,
    }
    if accept := request.headers.get("Accept"):
        proxy_headers["Accept"] = accept
    if content_type := request.headers.get("Content-Type"):
        proxy_headers["Content-Type"] = content_type
    proxy_response = await client.request_raw(
        request.method,
        request_path,
        body=await request.read(),
        query_params=request.query,
        headers=proxy_headers,
    )
    return web.Response(
        status=proxy_response["status"],
        body=proxy_response["body"],
        headers=proxy_response["headers"],
    )


class GrocyAIDashboardProxyView(HomeAssistantView):
    """Proxy dashboard HTML/API/static routes through the Home Assistant auth context."""

    requires_auth = True
    url = f"{PANEL_PROXY_URL_BASE}/{{path:.*}}"
    name = "api:grocy_ai_assistant:dashboard-proxy"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request, path: str = ""):
        return await self._handle(request, path)

    async def post(self, request, path: str = ""):
        return await self._handle(request, path)

    async def put(self, request, path: str = ""):
        return await self._handle(request, path)

    async def patch(self, request, path: str = ""):
        return await self._handle(request, path)

    async def delete(self, request, path: str = ""):
        return await self._handle(request, path)

    async def _handle(self, request, path: str):
        return await _proxy_dashboard_request(
            self.hass,
            request,
            path,
        )


class GrocyAIDashboardPictureProxyView(HomeAssistantView):
    """Proxy dashboard product pictures through the authenticated HA session."""

    # Product images stay behind Home Assistant auth. The native panel frontend
    # rewrites `/api/dashboard/product-picture?...` to this proxy route and then
    # loads the image bytes via an auth-bound `fetch(...)`, finally assigning a
    # short-lived `blob:` URL to `<img>` tags. Direct `<img src>` requests
    # against the authenticated HA proxy can return 401 in the panel runtime, so
    # we keep the endpoint closed and let the frontend perform the authenticated
    # fetch explicitly instead of exposing a public image proxy route.
    requires_auth = True
    url = PANEL_PICTURE_PROXY_URL
    name = "api:grocy_ai_assistant:dashboard-proxy:product-picture"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request):
        return await _proxy_dashboard_request(
            self.hass,
            request,
            "/api/dashboard/product-picture",
        )


async def async_setup(hass: HomeAssistant) -> None:
    """Register the Grocy AI dashboard as a native Home Assistant panel."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    panel_state = domain_data.setdefault(
        _PANEL_STATE_KEY,
        {
            "registrations": 0,
            "static_paths_registered": False,
            "panel_registered": False,
            "proxy_registered": False,
        },
    )

    if not panel_state["static_paths_registered"]:
        frontend_directory = _frontend_directory()
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    PANEL_FRONTEND_URL_BASE,
                    str(frontend_directory),
                    cache_headers=False,
                )
            ]
        )
        panel_state["static_paths_registered"] = True

    if not panel_state["proxy_registered"]:
        hass.http.register_view(GrocyAIDashboardPictureProxyView(hass))
        hass.http.register_view(GrocyAIDashboardProxyView(hass))
        panel_state["proxy_registered"] = True

    panel_state["registrations"] += 1
    panel_state["dashboard_api_base_path"] = PANEL_PROXY_URL_BASE
    panel_state["legacy_dashboard_emergency_url"] = f"{PANEL_PROXY_URL_BASE}/"

    if panel_state["panel_registered"]:
        async_remove_panel(hass, PANEL_SLUG)
    await async_register_panel(
        hass,
        frontend_url_path=PANEL_SLUG,
        webcomponent_name=PANEL_WEBCOMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{PANEL_FRONTEND_URL_BASE}/{PANEL_FRONTEND_MODULE}",
        config={
            "frontend_base_url": PANEL_FRONTEND_URL_BASE,
            "dashboard_api_base_path": PANEL_PROXY_URL_BASE,
            "dashboard_polling_interval_seconds": _resolve_active_config(hass).get(
                CONF_DASHBOARD_POLLING_INTERVAL_SECONDS,
                DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS,
            ),
            "panel_path": PANEL_PATH,
            "panel_title": PANEL_TITLE,
            "panel_icon": PANEL_ICON,
            "legacy_dashboard_emergency_url": f"{PANEL_PROXY_URL_BASE}/",
            "page_title": PANEL_TITLE,
            "route": f"/{PANEL_SLUG}",
            "sidebar_icon": PANEL_ICON,
            "sidebar_title": PANEL_TITLE,
            "integration_version": INTEGRATION_VERSION,
        },
    )
    panel_state["panel_registered"] = True


async def async_unload(hass: HomeAssistant) -> None:
    """Remove the Grocy AI dashboard panel when the last entry unloads."""
    domain_data = hass.data.get(DOMAIN, {})
    panel_state = domain_data.get(_PANEL_STATE_KEY)
    if not panel_state:
        return

    panel_state["registrations"] = max(0, panel_state["registrations"] - 1)
    if panel_state["registrations"] > 0:
        return

    if panel_state["panel_registered"]:
        async_remove_panel(hass, PANEL_SLUG)
    domain_data.pop(_PANEL_STATE_KEY, None)
