import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


class _FakeSensorEntity:
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


class _FakeHass:
    def __init__(self):
        self.data = {
            "grocy_ai_assistant": {
                "entry-1": {
                    "entity_runtime": {
                        "response": {
                            "state": "Bereit",
                            "icon": "mdi:comment-text-outline",
                            "attributes": {},
                        },
                        "response_time_last": {
                            "state": None,
                            "attributes": {"requests_count": 0},
                        },
                        "response_time_avg": {
                            "state": None,
                            "attributes": {"requests_count": 0},
                        },
                        "analysis_status": {"state": "Bereit", "attributes": {}},
                        "barcode_status": {"state": "Bereit", "attributes": {}},
                        "llava_status": {"state": "Bereit", "attributes": {}},
                        "product_input": {"value": ""},
                        "response_timing_stats": {"count": 0, "total_ms": 0.0},
                    }
                }
            }
        }


_RUNTIME_COORDINATORS = {}
_DISPATCHER_LISTENERS = {}


def _dispatcher_connect(_hass, signal, callback):
    listeners = _DISPATCHER_LISTENERS.setdefault(signal, [])
    listeners.append(callback)

    def _unsubscribe():
        listeners.remove(callback)

    return _unsubscribe


def _dispatcher_send(_hass, signal):
    for callback in list(_DISPATCHER_LISTENERS.get(signal, [])):
        callback()


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
    ha_dispatcher.async_dispatcher_connect = _dispatcher_connect
    ha_dispatcher.async_dispatcher_send = _dispatcher_send
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

    sys.modules["homeassistant"] = ha_module
    sys.modules["homeassistant.components"] = ha_components
    sys.modules["homeassistant.components.sensor"] = ha_sensor
    sys.modules["homeassistant.const"] = ha_const
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.dispatcher"] = ha_dispatcher
    sys.modules["homeassistant.helpers.entity"] = ha_entity
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_update_coordinator


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
    _load_module(f"{PACKAGE_NAME}.runtime", "runtime.py")
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

    assert sensor.native_value == "Keine Vorschläge"


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
    assert sensor.native_value == "Offline"
    assert (
        sensor.extra_state_attributes["last_error"]
        == "Status-Endpunkt nicht erreichbar"
    )


def test_analysis_status_sensor_reads_runtime_payload():
    sensor = sensor_module.GrocyAIAnalysisStatusSensor(_FakeEntry())
    sensor.hass = _FakeHass()
    sensor.hass.data["grocy_ai_assistant"]["entry-1"]["entity_runtime"][
        "analysis_status"
    ] = {
        "state": "Erfolgreich",
        "attributes": {"query": "Tomaten"},
    }

    assert sensor.native_value == "Erfolgreich"
    assert sensor.extra_state_attributes == {"query": "Tomaten"}


def test_response_sensor_updates_via_dispatcher_signal():
    hass = _FakeHass()
    sensor = sensor_module.GrocyAIResponseSensor(_FakeEntry())
    sensor.hass = hass

    asyncio.run(sensor.async_added_to_hass())

    hass.data["grocy_ai_assistant"]["entry-1"]["entity_runtime"]["response"] = {
        "state": "KI analysiert…",
        "icon": "mdi:progress-clock",
        "attributes": {},
    }
    _dispatcher_send(hass, "grocy_ai_assistant_runtime_entry-1_response")

    assert sensor.native_value == "KI analysiert…"
    assert sensor.icon == "mdi:progress-clock"
    assert sensor._write_count == 1


def test_response_time_sensor_reads_request_count_from_runtime_payload():
    sensor = sensor_module.GrocyAILastResponseTimeSensor(_FakeEntry())
    sensor.hass = _FakeHass()
    sensor.hass.data["grocy_ai_assistant"]["entry-1"]["entity_runtime"][
        "response_time_last"
    ] = {
        "state": 123.4,
        "attributes": {"requests_count": 2},
    }

    assert sensor.native_value == 123.4
    assert sensor.extra_state_attributes == {"requests_count": 2}
