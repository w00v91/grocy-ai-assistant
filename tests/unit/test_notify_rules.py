from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "grocy_ai_assistant.custom_components.grocy_ai_assistant"
PACKAGE_PATH = ROOT / "grocy_ai_assistant" / "custom_components" / "grocy_ai_assistant"


def _load_notification_modules():
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_PATH)]
    sys.modules[PACKAGE_NAME] = package

    models_name = f"{PACKAGE_NAME}.notify_models"
    rules_name = f"{PACKAGE_NAME}.notify_rules"

    models_spec = importlib.util.spec_from_file_location(
        models_name, PACKAGE_PATH / "notify_models.py"
    )
    models_module = importlib.util.module_from_spec(models_spec)
    sys.modules[models_name] = models_module
    assert models_spec and models_spec.loader
    models_spec.loader.exec_module(models_module)

    rules_spec = importlib.util.spec_from_file_location(
        rules_name, PACKAGE_PATH / "notify_rules.py"
    )
    rules_module = importlib.util.module_from_spec(rules_spec)
    sys.modules[rules_name] = rules_module
    assert rules_spec and rules_spec.loader
    rules_spec.loader.exec_module(rules_module)

    return models_module, rules_module


def test_persistent_rule_creates_message_without_mobile_targets():
    models, rules = _load_notification_modules()
    engine = rules.NotificationRuleEngine()
    event = models.NotificationEvent(
        event_type="shopping_due",
        title="Einkauf fällig",
        message="Milch fehlt",
        created_at=datetime.utcnow(),
    )
    settings = models.NotificationSettings(
        targets=[],
        rules=[
            models.NotificationRule(
                id="rule-1",
                name="Persistent only",
                enabled=True,
                event_types=("shopping_due",),
                channels=(models.NotificationChannel.PERSISTENT,),
            )
        ],
    )

    messages = engine.evaluate(event, settings)

    assert len(messages) == 1
    assert messages[0].channels == (models.NotificationChannel.PERSISTENT,)
    assert messages[0].target.id == "persistent_notification"


def test_mixed_rule_creates_mobile_and_persistent_messages():
    models, rules = _load_notification_modules()
    engine = rules.NotificationRuleEngine()
    event = models.NotificationEvent(
        event_type="shopping_due",
        title="Einkauf fällig",
        message="Milch fehlt",
        created_at=datetime.utcnow(),
    )
    settings = models.NotificationSettings(
        targets=[
            models.NotificationTarget(
                id="notify.mobile_app_phone",
                service="notify.mobile_app_phone",
                display_name="Phone",
                platform="android",
                active=True,
            )
        ],
        rules=[
            models.NotificationRule(
                id="rule-2",
                name="Mixed",
                enabled=True,
                event_types=("shopping_due",),
                channels=(
                    models.NotificationChannel.MOBILE_PUSH,
                    models.NotificationChannel.PERSISTENT,
                ),
            )
        ],
    )

    messages = engine.evaluate(event, settings)

    assert len(messages) == 2
    assert {message.target.id for message in messages} == {
        "notify.mobile_app_phone",
        "persistent_notification",
    }
