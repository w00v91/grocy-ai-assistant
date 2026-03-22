from __future__ import annotations

import importlib.util
import sys
import types
import asyncio
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


def _load_notification_modules():
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_PATH)]
    sys.modules[PACKAGE_NAME] = package

    models_name = f"{PACKAGE_NAME}.notify_models"
    dispatcher_name = f"{PACKAGE_NAME}.notify_dispatcher"

    models_spec = importlib.util.spec_from_file_location(
        models_name, PACKAGE_PATH / "notify_models.py"
    )
    models_module = importlib.util.module_from_spec(models_spec)
    sys.modules[models_name] = models_module
    assert models_spec and models_spec.loader
    models_spec.loader.exec_module(models_module)

    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object
    sys.modules["homeassistant"] = types.ModuleType("homeassistant")
    sys.modules["homeassistant.core"] = ha_core

    dispatcher_spec = importlib.util.spec_from_file_location(
        dispatcher_name, PACKAGE_PATH / "notify_dispatcher.py"
    )
    dispatcher_module = importlib.util.module_from_spec(dispatcher_spec)
    sys.modules[dispatcher_name] = dispatcher_module
    assert dispatcher_spec and dispatcher_spec.loader
    dispatcher_spec.loader.exec_module(dispatcher_module)

    return models_module, dispatcher_module


class _FakeServices:
    def __init__(self, service_map):
        self._service_map = service_map
        self.calls = []

    def async_services(self):
        return self._service_map

    async def async_call(self, domain, service, service_data, blocking=True):
        self.calls.append((domain, service, service_data, blocking))


class _FakeHass:
    def __init__(self, service_map):
        self.services = _FakeServices(service_map)


def _build_message(models):
    return models.NotificationMessage(
        id="message-1",
        event=models.NotificationEvent(
            event_type="shopping_due",
            title="Titel",
            message="Nachricht",
            created_at=datetime.now(UTC),
        ),
        rule_id="rule-1",
        target=models.NotificationTarget(
            id="persistent_notification",
            service="persistent_notification.create",
            display_name="Home Assistant",
            platform="ha",
        ),
        channels=(models.NotificationChannel.PERSISTENT,),
        title="Titel",
        body="Nachricht",
        severity=models.NotificationSeverity.INFO,
        dedup_key="dedup-1",
    )


def test_dispatcher_uses_core_persistent_notification_service_when_available():
    models, dispatcher_module = _load_notification_modules()
    hass = _FakeHass({"persistent_notification": {"create": object()}})
    dispatcher = dispatcher_module.NotificationDispatcher(hass)

    asyncio.run(dispatcher.async_dispatch(_build_message(models)))

    assert hass.services.calls[0][0:2] == ("persistent_notification", "create")


def test_dispatcher_falls_back_to_notify_persistent_notification_service():
    models, dispatcher_module = _load_notification_modules()
    hass = _FakeHass({"notify": {"persistent_notification": object()}})
    dispatcher = dispatcher_module.NotificationDispatcher(hass)

    asyncio.run(dispatcher.async_dispatch(_build_message(models)))

    assert hass.services.calls[0][0:2] == ("notify", "persistent_notification")
