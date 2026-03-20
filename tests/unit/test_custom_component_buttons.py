import asyncio
import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


class _FakeButtonEntity:
    @property
    def name(self):
        return getattr(self, "_attr_name", None)


class _FakeEntry:
    entry_id = "entry-1"
    data = {}
    options = {}


def _ensure_stubbed_homeassistant_modules():
    ha_module = types.ModuleType("homeassistant")
    ha_components = types.ModuleType("homeassistant.components")
    ha_button = types.ModuleType("homeassistant.components.button")

    ha_button.ButtonEntity = _FakeButtonEntity

    sys.modules.setdefault("homeassistant", ha_module)
    sys.modules.setdefault("homeassistant.components", ha_components)
    sys.modules.setdefault("homeassistant.components.button", ha_button)


def _load_module(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        module_name,
        PACKAGE_PATH / filename,
        submodule_search_locations=[str(PACKAGE_PATH)],
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_button_module():
    _ensure_stubbed_homeassistant_modules()

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_PATH)]
    sys.modules[PACKAGE_NAME] = package

    _load_module(f"{PACKAGE_NAME}.const", "const.py")
    _load_module(f"{PACKAGE_NAME}.addon_client", "addon_client.py")
    return _load_module(f"{PACKAGE_NAME}.button", "button.py")


button_module = _load_button_module()


class _StaticClient:
    def __init__(self, payload):
        self._payload = payload

    async def rebuild_catalog(self):
        return self._payload

    async def test_notifications(self):
        return self._payload


def test_catalog_rebuild_button_calls_v1_endpoint_client():
    button = button_module.GrocyAICatalogRebuildButton(_FakeEntry())
    button._build_client = lambda: _StaticClient({"_http_status": 200, "success": True})

    asyncio.run(button.async_press())

    assert button.name == "Grocy AI Katalog neu aufbauen"


def test_notification_test_button_raises_on_backend_error():
    button = button_module.GrocyAINotificationTestButton(_FakeEntry())
    button._build_client = lambda: _StaticClient(
        {"_http_status": 500, "detail": "kaputt"}
    )

    try:
        asyncio.run(button.async_press())
    except RuntimeError as error:
        assert str(error) == "kaputt"
    else:
        raise AssertionError("RuntimeError expected")
