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


def _load_panel_module(monkeypatch):
    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    http = types.ModuleType("homeassistant.components.http")
    panel_custom = types.ModuleType("homeassistant.components.panel_custom")
    core = types.ModuleType("homeassistant.core")

    calls = []

    def fake_register(*args, **kwargs):
        calls.append((args, kwargs))

    http.StaticPathConfig = _StaticPathConfig
    panel_custom.async_register_panel = fake_register
    core.HomeAssistant = object

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
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
    return module, calls


def test_panel_registers_native_module(monkeypatch):
    panel_module, calls = _load_panel_module(monkeypatch)

    import asyncio

    hass = _FakeHass()
    asyncio.run(panel_module.async_setup(hass, "http://example.local:8000"))

    _, kwargs = calls[0]
    assert kwargs["frontend_url_path"] == "grocy-ai"
    assert kwargs["webcomponent_name"] == "grocy-ai-dashboard-panel"
    assert kwargs["module_url"] == "/grocy_ai_assistant_panel/grocy-ai-dashboard.js"
    assert kwargs["sidebar_title"] == "Grocy AI"
    assert kwargs["sidebar_icon"] == "mdi:brain"
    assert (
        kwargs["config"]["legacy_dashboard_url"]
        == "/api/hassio_ingress/grocy_ai_assistant/"
    )
    assert kwargs["config"]["panel_path"] == "/grocy-ai"
    assert kwargs["config"]["panel_title"] == "Grocy AI"
    assert kwargs["config"]["panel_icon"] == "mdi:brain"


def test_panel_registers_static_bundle_directory(monkeypatch):
    panel_module, _ = _load_panel_module(monkeypatch)

    import asyncio

    hass = _FakeHass()
    asyncio.run(
        panel_module.async_setup(
            hass,
            "/api/hassio_ingress/71139b3d_grocy_ai_assistant",
        )
    )

    configs = hass.http.static_path_calls[0]
    assert len(configs) == 1
    assert configs[0].url_path == "/grocy_ai_assistant_panel"
    assert configs[0].path.endswith(
        "custom_components/grocy_ai_assistant/panel/frontend"
    )
    assert configs[0].cache_headers is False
