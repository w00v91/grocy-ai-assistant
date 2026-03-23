import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


class _FakeSensorEntity:
    def __init__(self, *args, **kwargs):
        self.hass = None
        self._remove_callbacks = []

    def async_on_remove(self, remove_callback):
        self._remove_callbacks.append(remove_callback)

    def async_write_ha_state(self):
        return None

    @property
    def name(self):
        return getattr(self, "_attr_name", None)

    @property
    def available(self):
        return getattr(self, "_attr_available", True)

    @property
    def native_value(self):
        return getattr(self, "_attr_native_value", None)

    @property
    def extra_state_attributes(self):
        return getattr(self, "_attr_extra_state_attributes", None)


class _FakeCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def available(self):
        return bool(getattr(self.coordinator, "last_update_success", False))


class _FakeSensorStateClass:
    MEASUREMENT = "measurement"


class _FakeEntityCategory:
    DIAGNOSTIC = "diagnostic"


class _FakeDeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class _FakeCoordinator:
    def __init__(
        self,
        data=None,
        *,
        last_update_success: bool = True,
        last_exception: Exception | None = None,
    ):
        self.data = data or {}
        self.last_update_success = last_update_success
        self.last_exception = last_exception


class _FakeEntry:
    entry_id = "entry-1"
    data = {}
    options = {}


class _FakeUpdateFailed(Exception):
    pass


_RUNTIME_COORDINATORS = {}


def _ensure_stubbed_homeassistant_modules():
    ha_module = types.ModuleType("homeassistant")
    ha_components = types.ModuleType("homeassistant.components")
    ha_sensor = types.ModuleType("homeassistant.components.sensor")
    ha_const = types.ModuleType("homeassistant.const")
    ha_config_entries = types.ModuleType("homeassistant.config_entries")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    ha_entity = types.ModuleType("homeassistant.helpers.entity")
    ha_update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    ha_sensor.SensorEntity = _FakeSensorEntity
    ha_sensor.SensorStateClass = _FakeSensorStateClass
    ha_const.EntityCategory = _FakeEntityCategory
    ha_config_entries.ConfigEntry = type("ConfigEntry", (), {})
    ha_core.HomeAssistant = type("HomeAssistant", (), {})
    ha_core.callback = lambda func: func
    ha_dispatcher.async_dispatcher_connect = lambda hass, signal, target: (lambda: None)
    ha_dispatcher.async_dispatcher_send = lambda hass, signal, *args: None
    ha_entity.EntityCategory = _FakeEntityCategory
    ha_entity.DeviceInfo = _FakeDeviceInfo
    ha_update_coordinator.CoordinatorEntity = _FakeCoordinatorEntity
    ha_update_coordinator.DataUpdateCoordinator = type(
        "DataUpdateCoordinator",
        (),
        {
            "__init__": lambda self, *args, **kwargs: None,
            "__class_getitem__": classmethod(lambda cls, item: cls),
        },
    )
    ha_update_coordinator.UpdateFailed = _FakeUpdateFailed

    sys.modules.setdefault("homeassistant", ha_module)
    sys.modules.setdefault("homeassistant.components", ha_components)
    sys.modules.setdefault("homeassistant.components.sensor", ha_sensor)
    sys.modules.setdefault("homeassistant.const", ha_const)
    sys.modules.setdefault("homeassistant.config_entries", ha_config_entries)
    sys.modules.setdefault("homeassistant.core", ha_core)
    sys.modules.setdefault("homeassistant.helpers", ha_helpers)
    sys.modules.setdefault("homeassistant.helpers.dispatcher", ha_dispatcher)
    sys.modules.setdefault("homeassistant.helpers.entity", ha_entity)
    sys.modules.setdefault(
        "homeassistant.helpers.update_coordinator", ha_update_coordinator
    )


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


def _load_sensor_module():
    _ensure_stubbed_homeassistant_modules()

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_PATH)]
    sys.modules[PACKAGE_NAME] = package

    coordinator_module = types.ModuleType(f"{PACKAGE_NAME}.coordinator")
    coordinator_module.COORDINATOR_STATUS = "status"
    coordinator_module.COORDINATOR_INVENTORY = "inventory"
    coordinator_module.COORDINATOR_RECIPE_SUGGESTIONS = "recipe_suggestions"
    coordinator_module.get_entry_coordinators = (
        lambda hass, entry_id: _RUNTIME_COORDINATORS[entry_id]
    )
    sys.modules[f"{PACKAGE_NAME}.coordinator"] = coordinator_module

    _load_module(f"{PACKAGE_NAME}.const", "const.py")
    _load_module(f"{PACKAGE_NAME}.entity", "entity.py")
    return _load_module(f"{PACKAGE_NAME}.sensor", "sensor.py")


sensor_module = _load_sensor_module()


def test_shopping_list_sensor_reads_count_and_attributes_from_inventory_coordinator():
    sensor = sensor_module.GrocyAIShoppingListOpenCountSensor(
        _FakeEntry(),
        _FakeCoordinator(
            data={
                "shopping_list_open_count": {
                    "state": 2,
                    "attributes": {"items": [{"id": 1}, {"id": 2}]},
                }
            }
        ),
    )

    assert sensor.available is True
    assert sensor.native_value == 2
    assert sensor.extra_state_attributes["items"] == [{"id": 1}, {"id": 2}]
    assert sensor.extra_state_attributes["last_update_success"] is True


def test_shopping_list_sensor_uses_coordinator_error_and_becomes_unavailable():
    sensor = sensor_module.GrocyAIShoppingListOpenCountSensor(
        _FakeEntry(),
        _FakeCoordinator(
            data={},
            last_update_success=False,
            last_exception=RuntimeError("Timeout beim Add-on"),
        ),
    )

    assert sensor.available is False
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert sensor.extra_state_attributes["last_error"] == "Timeout beim Add-on"


def test_recipe_sensor_uses_default_state_if_coordinator_has_no_payload():
    sensor = sensor_module.GrocyAITopAIRecipeSuggestionSensor(
        _FakeEntry(),
        _FakeCoordinator(data={}),
    )

    assert sensor.native_value == "none"


def test_top_grocy_recipe_sensor_only_exposes_best_matching_grocy_recipe():
    sensor = sensor_module.GrocyAITopGrocyRecipeSuggestionSensor(
        _FakeEntry(),
        _FakeCoordinator(
            data={
                "recipe_suggestion_top_grocy": {
                    "state": "Tomaten Pasta",
                    "attributes": {
                        "source": "grocy",
                        "recipes_count": 1,
                        "grocy_recipes": [
                            {"title": "Tomaten Pasta", "source": "grocy"}
                        ],
                        "ai_recipes": [],
                    },
                }
            }
        ),
    )

    assert sensor.available is True
    assert sensor.native_value == "Tomaten Pasta"
    assert sensor.extra_state_attributes["source"] == "grocy"
    assert sensor.extra_state_attributes["recipes_count"] == 1
    assert sensor.extra_state_attributes["grocy_recipes"] == [
        {"title": "Tomaten Pasta", "source": "grocy"}
    ]
    assert sensor.extra_state_attributes["ai_recipes"] == []


def test_status_sensor_uses_offline_fallback_when_status_coordinator_has_failed():
    sensor = sensor_module.GrocyAISensor(
        _FakeEntry(),
        _FakeCoordinator(
            data={},
            last_update_success=False,
            last_exception=RuntimeError("Status-Endpunkt nicht erreichbar"),
        ),
    )

    assert sensor.available is False
    assert sensor.native_value == "offline"
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert (
        sensor.extra_state_attributes["last_error"]
        == "Status-Endpunkt nicht erreichbar"
    )


def test_update_required_sensor_uses_unknown_fallback_when_status_coordinator_fails():
    sensor = sensor_module.GrocyAIUpdateRequiredSensor(
        _FakeEntry(),
        _FakeCoordinator(
            data={},
            last_update_success=False,
            last_exception=RuntimeError("Status-Endpunkt nicht erreichbar"),
        ),
    )

    assert sensor.available is False
    assert sensor.native_value == "unknown"
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert (
        sensor.extra_state_attributes["last_error"]
        == "Status-Endpunkt nicht erreichbar"
    )


def test_expiring_stock_sensor_uses_zero_fallback_when_inventory_coordinator_fails():
    sensor = sensor_module.GrocyAIExpiringStockProductCountSensor(
        _FakeEntry(),
        _FakeCoordinator(
            data={},
            last_update_success=False,
            last_exception=RuntimeError("Lager-Endpunkt nicht erreichbar"),
        ),
    )

    assert sensor.available is False
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert (
        sensor.extra_state_attributes["last_error"] == "Lager-Endpunkt nicht erreichbar"
    )


def test_async_setup_entry_wires_entry_scoped_coordinators_into_entities():
    _RUNTIME_COORDINATORS[_FakeEntry.entry_id] = {
        "status": _FakeCoordinator(),
        "inventory": _FakeCoordinator(),
        "recipe_suggestions": _FakeCoordinator(),
    }
    hass = types.SimpleNamespace(
        data={
            "grocy_ai_assistant": {
                _FakeEntry.entry_id: {
                    "coordinators": _RUNTIME_COORDINATORS[_FakeEntry.entry_id]
                }
            }
        }
    )
    added_entities = []

    async def _run_setup():
        await sensor_module.async_setup_entry(
            hass,
            _FakeEntry(),
            lambda entities: added_entities.extend(entities),
        )

    asyncio.run(_run_setup())

    assert added_entities
    assert isinstance(added_entities[0], sensor_module.GrocyAISensor)
    assert (
        added_entities[0].coordinator
        is _RUNTIME_COORDINATORS[_FakeEntry.entry_id]["status"]
    )
    assert (
        added_entities[5].coordinator
        is _RUNTIME_COORDINATORS[_FakeEntry.entry_id]["inventory"]
    )


def test_entities_expose_translation_keys_and_entity_names():
    response_sensor = sensor_module.GrocyAIResponseSensor(_FakeEntry())
    update_sensor = sensor_module.GrocyAIUpdateRequiredSensor(
        _FakeEntry(),
        _FakeCoordinator(),
    )

    assert response_sensor._attr_translation_key == "response_text"
    assert response_sensor._attr_has_entity_name is True
    assert update_sensor._attr_translation_key == "home_assistant_update_required"
    assert update_sensor._attr_has_entity_name is True


def test_all_sensor_types_share_the_entry_device_info():
    response_sensor = sensor_module.GrocyAIResponseSensor(_FakeEntry())
    shopping_sensor = sensor_module.GrocyAIShoppingListOpenCountSensor(
        _FakeEntry(), _FakeCoordinator()
    )
    average_sensor = sensor_module.GrocyAIAverageResponseTimeSensor(_FakeEntry())

    expected = {
        "identifiers": {("grocy_ai_assistant", "entry-1")},
        "name": "Grocy AI Assistant",
        "manufacturer": "Eigene Integration",
    }

    assert response_sensor.device_info == expected
    assert shopping_sensor.device_info == expected
    assert average_sensor.device_info == expected


def test_response_sensor_reads_runtime_payload_from_entry_state():
    response_sensor = sensor_module.GrocyAIResponseSensor(_FakeEntry())
    response_sensor.hass = types.SimpleNamespace(
        data={
            "grocy_ai_assistant": {
                "entry-1": {
                    "runtime_state": {
                        "response": {
                            "state": "processing",
                            "attributes": {
                                "icon": "mdi:progress-clock",
                                "step": "sync",
                            },
                        }
                    }
                }
            }
        }
    )

    assert response_sensor.native_value == "processing"
    assert response_sensor.extra_state_attributes["step"] == "sync"
    assert response_sensor.icon == "mdi:progress-clock"


def test_timing_sensors_read_centralized_runtime_metrics():
    last_sensor = sensor_module.GrocyAILastResponseTimeSensor(_FakeEntry())
    average_sensor = sensor_module.GrocyAIAverageResponseTimeSensor(_FakeEntry())
    hass = types.SimpleNamespace(
        data={
            "grocy_ai_assistant": {
                "entry-1": {
                    "runtime_state": {
                        "response_timing": {
                            "count": 3,
                            "total_ms": 420.0,
                            "last_ms": 160.5,
                            "average_ms": 140.0,
                        }
                    }
                }
            }
        }
    )
    last_sensor.hass = hass
    average_sensor.hass = hass

    assert last_sensor.native_value == 160.5
    assert average_sensor.native_value == 140.0
    assert last_sensor.extra_state_attributes["requests_count"] == 3
    assert average_sensor.extra_state_attributes["requests_count"] == 3
