import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


class _FakeTextEntity:
    def async_write_ha_state(self):
        return None


class _FakeDeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class _FakeEntry:
    entry_id = "entry-1"


def _ensure_stubbed_homeassistant_modules():
    ha_module = types.ModuleType("homeassistant")
    ha_components = types.ModuleType("homeassistant.components")
    ha_text = types.ModuleType("homeassistant.components.text")
    ha_config_entries = types.ModuleType("homeassistant.config_entries")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_entity = types.ModuleType("homeassistant.helpers.entity")

    ha_text.TextEntity = _FakeTextEntity
    ha_config_entries.ConfigEntry = object
    ha_core.HomeAssistant = object
    ha_entity.DeviceInfo = _FakeDeviceInfo

    sys.modules.setdefault("homeassistant", ha_module)
    sys.modules.setdefault("homeassistant.components", ha_components)
    sys.modules.setdefault("homeassistant.components.text", ha_text)
    sys.modules.setdefault("homeassistant.config_entries", ha_config_entries)
    sys.modules.setdefault("homeassistant.core", ha_core)
    sys.modules.setdefault("homeassistant.helpers", ha_helpers)
    sys.modules.setdefault("homeassistant.helpers.entity", ha_entity)


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


def _load_text_module():
    _ensure_stubbed_homeassistant_modules()

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_PATH)]
    sys.modules[PACKAGE_NAME] = package

    _load_module(f"{PACKAGE_NAME}.const", "const.py")
    _load_module(f"{PACKAGE_NAME}.entity", "entity.py")
    return _load_module(f"{PACKAGE_NAME}.text", "text.py")


text_module = _load_text_module()


def test_text_entity_registers_on_entry_device():
    entity = text_module.GrocyProductInput(_FakeEntry())

    assert entity.device_info == {
        "identifiers": {("grocy_ai_assistant", "entry-1")},
        "name": "Grocy AI Assistant",
        "manufacturer": "Eigene Integration",
    }


def test_text_entity_uses_translated_entity_name():
    entity = text_module.GrocyProductInput(_FakeEntry())

    assert entity._attr_translation_key == "product_input"
    assert entity._attr_has_entity_name is True
