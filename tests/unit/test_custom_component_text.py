import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


class _FakeTextEntity:
    def __init__(self, *args, **kwargs):
        self.hass = None
        self._remove_callbacks = []

    async def async_added_to_hass(self):
        return None

    def async_write_ha_state(self):
        return None

    def async_on_remove(self, remove_callback):
        self._remove_callbacks.append(remove_callback)


class _FakeRestoreEntity:
    async def async_added_to_hass(self):
        return None

    async def async_get_last_state(self):
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
    ha_dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    ha_entity = types.ModuleType("homeassistant.helpers.entity")
    ha_restore_state = types.ModuleType("homeassistant.helpers.restore_state")

    ha_text.TextEntity = _FakeTextEntity
    ha_config_entries.ConfigEntry = object
    ha_core.HomeAssistant = object
    ha_core.callback = lambda func: func
    ha_dispatcher.async_dispatcher_connect = lambda hass, signal, target: (lambda: None)
    ha_dispatcher.async_dispatcher_send = lambda hass, signal, *args: None
    ha_entity.DeviceInfo = _FakeDeviceInfo
    ha_restore_state.RestoreEntity = _FakeRestoreEntity

    sys.modules.setdefault("homeassistant", ha_module)
    sys.modules.setdefault("homeassistant.components", ha_components)
    sys.modules.setdefault("homeassistant.components.text", ha_text)
    sys.modules.setdefault("homeassistant.config_entries", ha_config_entries)
    sys.modules.setdefault("homeassistant.core", ha_core)
    sys.modules.setdefault("homeassistant.helpers", ha_helpers)
    sys.modules.setdefault("homeassistant.helpers.dispatcher", ha_dispatcher)
    sys.modules.setdefault("homeassistant.helpers.entity", ha_entity)
    sys.modules.setdefault("homeassistant.helpers.restore_state", ha_restore_state)


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
        "name": "Grocy AI Assistant Add-on",
        "manufacturer": "Grocy AI Assistant",
        "model": "Grocy AI Assistant Add-on",
        "model_id": "grocy_ai_assistant_addon",
    }


def test_text_entity_uses_translated_entity_name():
    entity = text_module.GrocyProductInput(_FakeEntry())

    assert entity._attr_translation_key == "product_input"
    assert entity._attr_has_entity_name is True


def test_text_entity_device_info_includes_addon_version_and_configuration_url():
    entity = text_module.GrocyProductInput(_FakeEntry())
    entity.hass = types.SimpleNamespace(
        data={
            "grocy_ai_assistant": {
                "entry-1": {
                    "config": {"api_base_url": "http://addon.local:8000"},
                    "coordinators": {
                        "status": types.SimpleNamespace(
                            data={
                                "status": {
                                    "attributes": {"addon_version": "8.0.50"}
                                }
                            }
                        )
                    },
                }
            }
        }
    )

    assert entity.device_info["sw_version"] == "8.0.50"
    assert entity.device_info["configuration_url"] == "http://addon.local:8000"


def test_text_entity_reads_runtime_value_from_hass_data():
    entity = text_module.GrocyProductInput(_FakeEntry())
    entity.hass = types.SimpleNamespace(
        data={
            "grocy_ai_assistant": {
                "entry-1": {
                    "runtime_state": {
                        "product_input": "Hafermilch",
                    }
                }
            }
        }
    )

    assert text_module.get_product_input_value(entity.hass, "entry-1") == "Hafermilch"
