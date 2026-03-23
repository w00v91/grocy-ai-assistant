import asyncio
import importlib.util
import sys
import types
from pathlib import Path


class _StaticPathConfig:
    def __init__(self, url_path, path, cache_headers=True):
        self.url_path = url_path
        self.path = path
        self.cache_headers = cache_headers


class _FakeHTTP:
    def __init__(self):
        self.static_path_calls = []
        self.registered_views = []

    async def async_register_static_paths(self, configs):
        self.static_path_calls.append(configs)

    def register_view(self, view):
        self.registered_views.append(view)


class _FakeHass:
    def __init__(self):
        self.http = _FakeHTTP()
        self.data = {}


def _load_panel_module(monkeypatch):
    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    frontend = types.ModuleType("homeassistant.components.frontend")
    http = types.ModuleType("homeassistant.components.http")
    panel_custom = types.ModuleType("homeassistant.components.panel_custom")
    core = types.ModuleType("homeassistant.core")

    register_calls = []
    remove_calls = []

    async def fake_register(*args, **kwargs):
        register_calls.append((args, kwargs))

    def fake_remove(*args, **kwargs):
        remove_calls.append((args, kwargs))

    frontend.async_remove_panel = fake_remove
    http.HomeAssistantView = object
    http.StaticPathConfig = _StaticPathConfig
    panel_custom.async_register_panel = fake_register
    core.HomeAssistant = object

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
    monkeypatch.setitem(sys.modules, "homeassistant.components.frontend", frontend)
    monkeypatch.setitem(sys.modules, "homeassistant.components.http", http)
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.panel_custom", panel_custom
    )
    monkeypatch.setitem(sys.modules, "homeassistant.core", core)

    package_name = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
    package = types.ModuleType(package_name)
    package.__path__ = []
    monkeypatch.setitem(sys.modules, package_name, package)

    const_module = types.ModuleType(f"{package_name}.const")
    const_module.CONF_API_BASE_URL = "api_base_url"
    const_module.DEFAULT_ADDON_BASE_URL = "http://local-grocy-ai-assistant:8000"
    const_module.CONF_DASHBOARD_POLLING_INTERVAL_SECONDS = (
        "dashboard_polling_interval_seconds"
    )
    const_module.DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS = 5
    const_module.DOMAIN = "grocy_ai_assistant"
    const_module.INTEGRATION_VERSION = "8.0.10"
    monkeypatch.setitem(sys.modules, f"{package_name}.const", const_module)

    addon_client_module = types.ModuleType(f"{package_name}.addon_client")
    addon_client_instances = []

    class _AddonClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.calls = []
            addon_client_instances.append(self)

        async def request_raw(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return {
                "status": 200,
                "body": b"{}",
                "headers": {"Content-Type": "application/json"},
            }

    addon_client_module.AddonClient = _AddonClient
    monkeypatch.setitem(
        sys.modules, f"{package_name}.addon_client", addon_client_module
    )

    module_path = (
        Path(__file__).resolve().parents[2]
        / "grocy_ai_assistant"
        / "custom_components"
        / "grocy_ai_assistant"
        / "panel.py"
    )
    spec = importlib.util.spec_from_file_location(
        f"{package_name}.panel",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module, register_calls, remove_calls, addon_client_instances


def test_panel_registers_native_module_metadata(monkeypatch):
    panel_module, register_calls, remove_calls, _ = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass))

    assert remove_calls == []

    _, kwargs = register_calls[0]
    assert kwargs["frontend_url_path"] == "grocy-ai"
    assert kwargs["webcomponent_name"] == "grocy-ai-dashboard-panel"
    assert kwargs["module_url"] == "/grocy_ai_assistant_panel/grocy-ai-dashboard.js"
    assert kwargs["sidebar_title"] == "Grocy AI"
    assert kwargs["sidebar_icon"] == "mdi:fridge-outline"
    assert (
        kwargs["config"]["dashboard_api_base_path"]
        == "/api/grocy_ai_assistant/dashboard-proxy"
    )
    assert kwargs["config"]["dashboard_polling_interval_seconds"] == 5
    assert (
        kwargs["config"]["legacy_dashboard_emergency_url"]
        == "/api/grocy_ai_assistant/dashboard-proxy/"
    )
    assert kwargs["config"]["panel_path"] == "/grocy-ai"
    assert kwargs["config"]["panel_title"] == "Grocy AI"
    assert kwargs["config"]["panel_icon"] == "mdi:fridge-outline"
    assert kwargs["config"]["page_title"] == "Grocy AI"
    assert kwargs["config"]["route"] == "/grocy-ai"
    assert kwargs["config"]["sidebar_title"] == "Grocy AI"
    assert kwargs["config"]["sidebar_icon"] == "mdi:fridge-outline"


def test_panel_registers_dashboard_proxy_view_once(monkeypatch):
    panel_module, _, _, _ = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass))
    asyncio.run(panel_module.async_setup(hass))

    assert len(hass.http.registered_views) == 2
    assert hass.http.registered_views[0].url == panel_module.PANEL_PICTURE_PROXY_URL
    assert hass.http.registered_views[0].requires_auth is False
    assert (
        hass.http.registered_views[1].url
        == "/api/grocy_ai_assistant/dashboard-proxy/{path:.*}"
    )
    assert hass.http.registered_views[1].requires_auth is True


def test_panel_registers_static_bundle_route_once(monkeypatch):
    panel_module, _, _, _ = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass))
    asyncio.run(panel_module.async_setup(hass))

    assert len(hass.http.static_path_calls) == 1
    configs = hass.http.static_path_calls[0]
    assert len(configs) == 1
    assert configs[0].url_path == "/grocy_ai_assistant_panel"
    assert configs[0].path.endswith(
        "custom_components/grocy_ai_assistant/panel/frontend"
    )
    assert configs[0].cache_headers is False


def test_panel_unload_removes_sidebar_entry_when_last_registration_is_gone(monkeypatch):
    panel_module, _, remove_calls, _ = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass))
    asyncio.run(panel_module.async_setup(hass))

    asyncio.run(panel_module.async_unload(hass))
    assert [call[0] for call in remove_calls].count((hass, "grocy-ai")) == 1

    asyncio.run(panel_module.async_unload(hass))
    assert [call[0] for call in remove_calls].count((hass, "grocy-ai")) == 2
    assert panel_module._PANEL_STATE_KEY not in hass.data["grocy_ai_assistant"]


def test_panel_reregisters_without_unknown_panel_remove_on_first_setup(monkeypatch):
    panel_module, register_calls, remove_calls, _ = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass))
    asyncio.run(panel_module.async_setup(hass))

    assert len(register_calls) == 2
    assert [call[0] for call in remove_calls] == [(hass, "grocy-ai")]


def test_panel_resolves_nested_entry_config_for_dashboard_metadata_and_client(
    monkeypatch,
):
    panel_module, register_calls, _, addon_client_instances = _load_panel_module(
        monkeypatch
    )

    hass = _FakeHass()
    hass.data["grocy_ai_assistant"] = {
        "entry-1": {
            "config": {
                "api_key": "secret-token",
                "api_base_url": "http://addon.local:8123",
                "dashboard_polling_interval_seconds": 15,
            },
            "coordinators": {},
        }
    }

    asyncio.run(panel_module.async_setup(hass))

    _, kwargs = register_calls[0]
    assert kwargs["config"]["dashboard_polling_interval_seconds"] == 15

    class _FakeRequest:
        method = "GET"
        query = {}
        headers = {}

        async def read(self):
            return b""

    response = asyncio.run(
        hass.http.registered_views[1].get(_FakeRequest(), "api/test")
    )

    assert response.status == 200
    assert addon_client_instances
    assert addon_client_instances[-1].args[0] == "http://addon.local:8123"
    assert addon_client_instances[-1].args[1] == "secret-token"


def test_native_shopping_hero_renders_einkauf_eyebrow_above_search_title():
    source = (
        Path(__file__).resolve().parents[2]
        / "grocy_ai_assistant"
        / "custom_components"
        / "grocy_ai_assistant"
        / "panel"
        / "frontend"
        / "grocy-ai-dashboard.js"
    ).read_text()

    assert "heroEyebrow.textContent = 'Einkauf';" in source
    assert "heroCopy.append(heroEyebrow, heroTitle);" in source
    assert "listEyebrow.textContent = 'Einkauf';" not in source
    assert "listCopy.append(listTitle);" in source


def test_public_product_picture_proxy_forwards_get_without_ha_auth(monkeypatch):
    panel_module, _, _, addon_client_instances = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass))

    picture_proxy_view = hass.http.registered_views[0]

    class _FakeRequest:
        method = "GET"
        query = {
            "src": "http://homeassistant.local:9192/api/files/productpictures/test.png",
            "size": "thumb",
        }
        headers = {"Accept": "image/png"}

        async def read(self):
            return b""

    response = asyncio.run(picture_proxy_view.get(_FakeRequest()))

    assert response.status == 200
    assert addon_client_instances
    args, kwargs = addon_client_instances[-1].calls[0]
    assert args == ("GET", "/api/dashboard/product-picture")
    assert kwargs["query_params"] == _FakeRequest.query
    assert kwargs["headers"]["Accept"] == "image/png"
    assert (
        kwargs["headers"]["X-Ingress-Path"] == "/api/grocy_ai_assistant/dashboard-proxy"
    )
