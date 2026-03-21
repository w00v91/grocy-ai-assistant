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

    async def async_register_static_paths(self, configs):
        self.static_path_calls.append(configs)


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
    const_module.DEFAULT_ADDON_INGRESS_PATH = "/api/hassio_ingress/grocy_ai_assistant/"
    const_module.DOMAIN = "grocy_ai_assistant"
    monkeypatch.setitem(sys.modules, f"{package_name}.const", const_module)

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
    return module, register_calls, remove_calls


def test_panel_registers_native_module_metadata(monkeypatch):
    panel_module, register_calls, remove_calls = _load_panel_module(monkeypatch)

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
        kwargs["config"]["legacy_dashboard_url"]
        == "/api/hassio_ingress/grocy_ai_assistant/"
    )
    assert kwargs["config"]["panel_path"] == "/grocy-ai"
    assert kwargs["config"]["panel_title"] == "Grocy AI"
    assert kwargs["config"]["panel_icon"] == "mdi:fridge-outline"
    assert kwargs["config"]["page_title"] == "Grocy AI"
    assert kwargs["config"]["route"] == "/grocy-ai"
    assert kwargs["config"]["sidebar_title"] == "Grocy AI"
    assert kwargs["config"]["sidebar_icon"] == "mdi:fridge-outline"


def test_panel_registers_static_bundle_route_once(monkeypatch):
    panel_module, _, _ = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(
        panel_module.async_setup(hass)
    )
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
    panel_module, _, remove_calls = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass))
    asyncio.run(panel_module.async_setup(hass))

    asyncio.run(panel_module.async_unload(hass))
    assert [call[0] for call in remove_calls].count((hass, "grocy-ai")) == 1

    asyncio.run(panel_module.async_unload(hass))
    assert [call[0] for call in remove_calls].count((hass, "grocy-ai")) == 2
    assert panel_module._PANEL_STATE_KEY not in hass.data["grocy_ai_assistant"]


def test_panel_reregisters_without_unknown_panel_remove_on_first_setup(monkeypatch):
    panel_module, register_calls, remove_calls = _load_panel_module(monkeypatch)

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass))
    asyncio.run(panel_module.async_setup(hass))

    assert len(register_calls) == 2
    assert [call[0] for call in remove_calls] == [(hass, "grocy-ai")]
