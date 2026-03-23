import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


class _FakeTextEntity:
    def __init__(self):
        self.hass = None
        self._remove_callbacks = []
        self._write_count = 0

    def async_write_ha_state(self):
        if not hasattr(self, "_write_count"):
            self._write_count = 0
        self._write_count += 1

    def async_on_remove(self, callback):
        if not hasattr(self, "_remove_callbacks"):
            self._remove_callbacks = []
        self._remove_callbacks.append(callback)


class _FakeDeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class _FakeEntry:
    entry_id = "entry-1"


class _FakeHass:
    def __init__(self):
        self.data = {
            "grocy_ai_assistant": {
                "entry-1": {
                    "entity_runtime": {
                        "product_input": {"value": "Milch"},
                    }
                }
            }
        }


def _dispatcher_send(_hass, _signal):
    return None


def _ensure_stubbed_homeassistant_modules():
    ha_module = types.ModuleType("homeassistant")
    ha_components = types.ModuleType("homeassistant.components")
    ha_text = types.ModuleType("homeassistant.components.text")
    ha_config_entries = types.ModuleType("homeassistant.config_entries")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    ha_entity = types.ModuleType("homeassistant.helpers.entity")

    ha_text.TextEntity = _FakeTextEntity
    ha_config_entries.ConfigEntry = object
    ha_core.HomeAssistant = object
    ha_dispatcher.async_dispatcher_send = _dispatcher_send
    ha_entity.DeviceInfo = _FakeDeviceInfo

    sys.modules["homeassistant"] = ha_module
    sys.modules["homeassistant.components"] = ha_components
    sys.modules["homeassistant.components.text"] = ha_text
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.dispatcher"] = ha_dispatcher
    sys.modules["homeassistant.helpers.entity"] = ha_entity


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
    _load_module(f"{PACKAGE_NAME}.runtime", "runtime.py")
    return _load_module(f"{PACKAGE_NAME}.text", "text.py")


text_module = _load_text_module()


def test_text_entity_registers_on_entry_device():
    entity = text_module.GrocyProductInput(_FakeEntry())

    assert entity.device_info == {
        "identifiers": {("grocy_ai_assistant", "entry-1")},
        "name": "Grocy AI Assistant",
        "manufacturer": "Eigene Integration",
    }


def test_text_entity_reads_initial_runtime_value_and_registers_itself():
    hass = _FakeHass()
    entity = text_module.GrocyProductInput(_FakeEntry())
    entity.hass = hass

    asyncio.run(entity.async_added_to_hass())

    assert entity.native_value == "Milch"
    assert text_module.get_product_input_entity(hass, "entry-1") is entity


def test_text_entity_async_set_value_updates_runtime_store():
    hass = _FakeHass()
    entity = text_module.GrocyProductInput(_FakeEntry())
    entity.hass = hass
    asyncio.run(entity.async_added_to_hass())

    asyncio.run(entity.async_set_value("Tomaten"))

    assert (
        hass.data["grocy_ai_assistant"]["entry-1"]["entity_runtime"]["product_input"][
            "value"
        ]
        == "Tomaten"
    )
    assert entity.native_value == "Tomaten"
    assert entity._write_count == 1


def test_async_set_product_input_value_uses_registered_entity_method():
    hass = _FakeHass()
    entity = text_module.GrocyProductInput(_FakeEntry())
    entity.hass = hass
    asyncio.run(entity.async_added_to_hass())

    asyncio.run(
        text_module.async_set_product_input_value(hass, "entry-1", "Hafermilch")
    )

    assert entity.native_value == "Hafermilch"
    assert (
        hass.data["grocy_ai_assistant"]["entry-1"]["entity_runtime"]["product_input"][
            "value"
        ]
        == "Hafermilch"
    )
    assert entity._write_count == 1


def test_async_set_product_input_value_falls_back_to_runtime_without_entity():
    hass = _FakeHass()

    asyncio.run(text_module.async_set_product_input_value(hass, "entry-1", "Reis"))

    assert (
        hass.data["grocy_ai_assistant"]["entry-1"]["entity_runtime"]["product_input"][
            "value"
        ]
        == "Reis"
    )
