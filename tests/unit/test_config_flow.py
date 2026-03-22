import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest


class _VolInvalid(Exception):
    pass


class _Marker:
    def __init__(self, key, default=None):
        self.key = key
        self.default = default


class _Required(_Marker):
    pass


class _Optional(_Marker):
    pass


class _All:
    def __init__(self, *validators):
        self.validators = validators

    def __call__(self, value):
        result = value
        for validator in self.validators:
            result = validator(result)
        return result


class _Coerce:
    def __init__(self, expected_type):
        self.expected_type = expected_type

    def __call__(self, value):
        try:
            return self.expected_type(value)
        except (TypeError, ValueError) as error:
            raise _VolInvalid(str(error)) from error


class _Range:
    def __init__(self, *, min=None, max=None):
        self.min = min
        self.max = max

    def __call__(self, value):
        if self.min is not None and value < self.min:
            raise _VolInvalid(f"value must be at least {self.min}")
        if self.max is not None and value > self.max:
            raise _VolInvalid(f"value must be at most {self.max}")
        return value


class _Schema:
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, value):
        result = {}
        for marker, validator in self.schema.items():
            key = marker.key if isinstance(marker, _Marker) else marker
            if key in value:
                candidate = value[key]
            elif isinstance(marker, _Marker) and marker.default is not None:
                candidate = marker.default
            else:
                raise _VolInvalid(f"missing required key: {key}")

            if validator is bool:
                result[key] = bool(candidate)
            elif validator is str:
                result[key] = str(candidate)
            elif callable(validator):
                result[key] = validator(candidate)
            else:
                result[key] = candidate
        return result


class _VolModule(types.ModuleType):
    Invalid = _VolInvalid
    Schema = _Schema
    All = _All
    Coerce = _Coerce
    Range = _Range

    @staticmethod
    def Required(key, default=None):
        return _Required(key, default=default)

    @staticmethod
    def Optional(key, default=None):
        return _Optional(key, default=default)


def _load_config_flow_module(monkeypatch):
    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    voluptuous = _VolModule("voluptuous")

    class _ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            return super().__init_subclass__()

    class _OptionsFlow:
        pass

    config_entries.ConfigFlow = _ConfigFlow
    config_entries.OptionsFlow = _OptionsFlow
    core.callback = lambda func: func

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.config_entries", config_entries)
    monkeypatch.setitem(sys.modules, "homeassistant.core", core)
    monkeypatch.setitem(sys.modules, "voluptuous", voluptuous)

    package_name = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
    package = types.ModuleType(package_name)
    package.__path__ = []
    monkeypatch.setitem(sys.modules, package_name, package)

    base_path = (
        Path(__file__).resolve().parents[2]
        / "grocy_ai_assistant"
        / "custom_components"
        / "grocy_ai_assistant"
    )

    const_spec = importlib.util.spec_from_file_location(
        f"{package_name}.const",
        base_path / "const.py",
    )
    const_module = importlib.util.module_from_spec(const_spec)
    assert const_spec and const_spec.loader
    const_spec.loader.exec_module(const_module)
    monkeypatch.setitem(sys.modules, f"{package_name}.const", const_module)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.config_flow",
        base_path / "config_flow.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module, voluptuous


def _capture_form_schema(flow):
    captured = {}

    def fake_show_form(*, step_id, data_schema):
        captured["step_id"] = step_id
        captured["schema"] = data_schema
        return captured

    flow.async_show_form = fake_show_form
    return captured


def test_options_flow_allows_zero_dashboard_polling_interval(monkeypatch):
    module, _ = _load_config_flow_module(monkeypatch)
    entry = types.SimpleNamespace(options={}, data={"api_key": "token"})
    flow = module.GrocyAIOptionsFlowHandler(entry)
    captured = _capture_form_schema(flow)

    result = asyncio.run(flow.async_step_init())

    assert result["step_id"] == "init"
    validated = captured["schema"](
        {
            module.CONF_API_KEY: "token",
            module.CONF_DASHBOARD_POLLING_INTERVAL_SECONDS: 0,
        }
    )
    assert validated[module.CONF_DASHBOARD_POLLING_INTERVAL_SECONDS] == 0


def test_options_flow_rejects_negative_dashboard_polling_interval(monkeypatch):
    module, voluptuous = _load_config_flow_module(monkeypatch)
    entry = types.SimpleNamespace(options={}, data={"api_key": "token"})
    flow = module.GrocyAIOptionsFlowHandler(entry)
    captured = _capture_form_schema(flow)

    asyncio.run(flow.async_step_init())

    with pytest.raises(voluptuous.Invalid):
        captured["schema"](
            {
                module.CONF_API_KEY: "token",
                module.CONF_DASHBOARD_POLLING_INTERVAL_SECONDS: -1,
            }
        )
