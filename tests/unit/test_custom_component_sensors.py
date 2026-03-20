import asyncio
import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


class _FakeSensorEntity:
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


class _FakeSensorStateClass:
    MEASUREMENT = "measurement"


class _FakeEntityCategory:
    DIAGNOSTIC = "diagnostic"


class _FakeEntry:
    entry_id = "entry-1"
    data = {}
    options = {}


def _ensure_stubbed_homeassistant_modules():
    ha_module = types.ModuleType("homeassistant")
    ha_components = types.ModuleType("homeassistant.components")
    ha_sensor = types.ModuleType("homeassistant.components.sensor")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_entity = types.ModuleType("homeassistant.helpers.entity")

    ha_sensor.SensorEntity = _FakeSensorEntity
    ha_sensor.SensorStateClass = _FakeSensorStateClass
    ha_entity.EntityCategory = _FakeEntityCategory

    sys.modules.setdefault("homeassistant", ha_module)
    sys.modules.setdefault("homeassistant.components", ha_components)
    sys.modules.setdefault("homeassistant.components.sensor", ha_sensor)
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


def _load_sensor_module():
    _ensure_stubbed_homeassistant_modules()

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_PATH)]
    sys.modules[PACKAGE_NAME] = package

    _load_module(f"{PACKAGE_NAME}.const", "const.py")
    _load_module(f"{PACKAGE_NAME}.entity_payloads", "entity_payloads.py")
    _load_module(f"{PACKAGE_NAME}.addon_client", "addon_client.py")
    return _load_module(f"{PACKAGE_NAME}.sensor", "sensor.py")


sensor_module = _load_sensor_module()


class _StaticClient:
    def __init__(self, payload=None, *, exc: Exception | None = None):
        self._payload = payload
        self._exc = exc

    async def get_shopping_list(self):
        if self._exc is not None:
            raise self._exc
        return self._payload

    async def get_recipe_suggestions(self, **kwargs):
        if self._exc is not None:
            raise self._exc
        return self._payload


def test_shopping_list_sensor_uses_fallback_value_on_http_error():
    sensor = sensor_module.GrocyAIShoppingListOpenCountSensor(_FakeEntry())
    sensor._build_client = lambda: _StaticClient(
        {"_http_status": 500, "detail": "Dashboard endpoint fehlgeschlagen"}
    )

    asyncio.run(sensor.async_update())

    assert sensor.available is True
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert sensor.extra_state_attributes["last_error"] == "Dashboard endpoint fehlgeschlagen"
    assert sensor.extra_state_attributes["http_status"] == 500


def test_shopping_list_sensor_preserves_last_successful_value_after_exception():
    sensor = sensor_module.GrocyAIShoppingListOpenCountSensor(_FakeEntry())
    sensor._build_client = lambda: _StaticClient(
        {"_http_status": 200, "items": [{"id": 1}, {"id": 2}]}
    )

    asyncio.run(sensor.async_update())

    assert sensor.available is True
    assert sensor.native_value == 2
    assert sensor.extra_state_attributes["last_update_success"] is True

    sensor._build_client = lambda: _StaticClient(exc=RuntimeError("Timeout beim Add-on"))
    asyncio.run(sensor.async_update())

    assert sensor.available is True
    assert sensor.native_value == 2
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert sensor.extra_state_attributes["last_error"] == "Timeout beim Add-on"


def test_recipe_sensor_exposes_default_state_instead_of_unavailable_on_http_error():
    sensor = sensor_module.GrocyAITopAIRecipeSuggestionSensor(_FakeEntry())
    sensor._build_client = lambda: _StaticClient(
        {"_http_status": 503, "detail": "Rezeptdienst nicht bereit"}
    )

    asyncio.run(sensor.async_update())

    assert sensor.available is True
    assert sensor.native_value == "Keine Vorschläge"
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert sensor.extra_state_attributes["last_error"] == "Rezeptdienst nicht bereit"
    assert sensor.extra_state_attributes["http_status"] == 503


def test_top_grocy_recipe_sensor_only_exposes_best_matching_grocy_recipe():
    sensor = sensor_module.GrocyAITopGrocyRecipeSuggestionSensor(_FakeEntry())
    sensor._build_client = lambda: _StaticClient(
        {
            "_http_status": 200,
            "selected_products": ["Tomate"],
            "grocy_recipes": [
                {"title": "Tomaten Pasta", "source": "grocy"},
                {"title": "Tomaten Suppe", "source": "grocy"},
            ],
            "ai_recipes": [
                {"title": "Tomatensalat", "source": "ai"},
            ],
        }
    )

    asyncio.run(sensor.async_update())

    assert sensor.available is True
    assert sensor.native_value == "Tomaten Pasta"
    assert sensor.extra_state_attributes["source"] == "grocy"
    assert sensor.extra_state_attributes["recipes_count"] == 1
    assert sensor.extra_state_attributes["grocy_recipes"] == [
        {"title": "Tomaten Pasta", "source": "grocy"}
    ]
    assert sensor.extra_state_attributes["ai_recipes"] == []


def test_status_sensor_uses_offline_fallback_on_initial_exception():
    sensor = sensor_module.GrocyAISensor(_FakeEntry())
    sensor._build_client = lambda: types.SimpleNamespace(
        get_status=_raise_runtime_error("Status-Endpunkt nicht erreichbar")
    )

    asyncio.run(sensor.async_update())

    assert sensor.available is True
    assert sensor.native_value == "Offline"
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert sensor.extra_state_attributes["last_error"] == "Status-Endpunkt nicht erreichbar"


def test_update_required_sensor_uses_unknown_fallback_on_initial_exception():
    sensor = sensor_module.GrocyAIUpdateRequiredSensor(_FakeEntry())
    sensor._build_client = lambda: types.SimpleNamespace(
        get_status=_raise_runtime_error("Status-Endpunkt nicht erreichbar")
    )

    asyncio.run(sensor.async_update())

    assert sensor.available is True
    assert sensor.native_value == "Unbekannt"
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert sensor.extra_state_attributes["last_error"] == "Status-Endpunkt nicht erreichbar"


def test_expiring_stock_sensor_uses_zero_fallback_on_initial_exception():
    sensor = sensor_module.GrocyAIExpiringStockProductCountSensor(_FakeEntry())
    sensor._build_client = lambda: types.SimpleNamespace(
        get_stock_products=_raise_runtime_error("Lager-Endpunkt nicht erreichbar")
    )

    asyncio.run(sensor.async_update())

    assert sensor.available is True
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes["last_update_success"] is False
    assert sensor.extra_state_attributes["last_error"] == "Lager-Endpunkt nicht erreichbar"


def _raise_runtime_error(message: str):
    async def _raiser():
        raise RuntimeError(message)

    return _raiser
