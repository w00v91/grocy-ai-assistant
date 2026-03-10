import importlib.util
import sys
import types
from pathlib import Path


def _load_panel_module(monkeypatch):
    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    frontend = types.ModuleType("homeassistant.components.frontend")
    core = types.ModuleType("homeassistant.core")

    calls = []

    def fake_register(*args, **kwargs):
        calls.append((args, kwargs))

    frontend.async_register_built_in_panel = fake_register
    core.HomeAssistant = object

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
    monkeypatch.setitem(sys.modules, "homeassistant.components.frontend", frontend)
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


def test_panel_keeps_http_urls_when_configured_explicitly(monkeypatch):
    panel_module, calls = _load_panel_module(monkeypatch)

    import asyncio
    asyncio.run(panel_module.async_setup(object(), "http://example.local:8000"))

    _, kwargs = calls[0]
    assert kwargs["config"]["url"] == "http://example.local:8000"


def test_panel_keeps_https_urls(monkeypatch):
    panel_module, calls = _load_panel_module(monkeypatch)

    import asyncio
    asyncio.run(panel_module.async_setup(object(), "https://example.org/dashboard"))

    _, kwargs = calls[0]
    assert kwargs["config"]["url"] == "https://example.org/dashboard"


def test_panel_adds_trailing_slash_for_ingress_paths(monkeypatch):
    panel_module, calls = _load_panel_module(monkeypatch)

    import asyncio
    asyncio.run(panel_module.async_setup(object(), "/api/hassio_ingress/71139b3d_grocy_ai_assistant"))

    _, kwargs = calls[0]
    assert kwargs["config"]["url"] == "/api/hassio_ingress/71139b3d_grocy_ai_assistant/"


def test_panel_uses_ingress_for_localhost_urls(monkeypatch):
    panel_module, calls = _load_panel_module(monkeypatch)

    import asyncio
    asyncio.run(panel_module.async_setup(object(), "http://localhost:8000"))

    _, kwargs = calls[0]
    assert kwargs["config"]["url"] == "/api/hassio_ingress/grocy_ai_assistant/"
