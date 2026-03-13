"""Application service layer for notifications.

Coordinates store, discovery, rule engine and dispatcher.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .notify_events import SUPPORTED_NOTIFICATION_EVENTS, create_notification_event
from .notify_dispatcher import NotificationDispatcher
from .notify_models import (
    NotificationChannel,
    NotificationMessage,
    NotificationRule,
    NotificationSettings,
    NotificationSeverity,
    NotificationTarget,
)
from .notify_rules import NotificationRuleEngine
from .notify_store import MAX_HISTORY_ENTRIES, NotificationStore

DATA_NOTIFICATION_MANAGER = "notification_manager"


class NotificationManager:
    """Entry-scoped notification orchestration service."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._store = NotificationStore(hass, entry_id)
        self._dispatcher = NotificationDispatcher(hass)
        self._rules = NotificationRuleEngine()
        self._settings = NotificationSettings()
        self._history = []

    @property
    def settings(self) -> NotificationSettings:
        return self._settings

    @property
    def history(self):
        return self._history

    async def async_initialize(self) -> None:
        settings, history = await self._store.async_load()
        self._settings = settings
        self._history = history
        await self.async_refresh_targets()

        if not self._settings.rules:
            self._settings.rules = [_default_rule()]
            self._settings.enabled_event_types = SUPPORTED_NOTIFICATION_EVENTS
            await self._save()

    async def async_refresh_targets(self) -> None:
        discovered = self._discover_mobile_targets()
        existing = {target.id: target for target in self._settings.targets}
        merged: list[NotificationTarget] = []

        for target in discovered:
            existing_target = existing.get(target.id)
            if existing_target:
                target.user_id = existing_target.user_id
                target.active = existing_target.active
            merged.append(target)

        self._settings.targets = merged
        await self._save()

    def _discover_mobile_targets(self) -> list[NotificationTarget]:
        services = self._hass.services.async_services().get("notify", {})
        targets: list[NotificationTarget] = []
        for service_name in services:
            if not service_name.startswith("mobile_app_"):
                continue
            target_id = f"notify.{service_name}"
            platform = "ios" if "iphone" in service_name else "android"
            display_name = (
                service_name.replace("mobile_app_", "").replace("_", " ").title()
            )
            targets.append(
                NotificationTarget(
                    id=target_id,
                    service=target_id,
                    display_name=display_name,
                    platform=platform,
                )
            )
        return targets

    async def async_process_event(self, event_type: str, payload: dict) -> int:
        if event_type not in SUPPORTED_NOTIFICATION_EVENTS:
            raise ValueError(f"Unsupported event type: {event_type}")

        event = create_notification_event(
            event_type,
            title=payload.get("title", "Grocy Update"),
            message=payload.get("message", "Ein neues Ereignis liegt vor."),
            payload=payload,
            severity=NotificationSeverity(
                payload.get("severity", NotificationSeverity.INFO.value)
            ),
            source=payload.get("source", "shopping"),
        )

        messages = self._rules.evaluate(event, self._settings)
        sent_count = 0
        for message in messages:
            history_entry = await self._dispatcher.async_dispatch(message)
            self._history.insert(0, history_entry)
            sent_count += int(history_entry.delivered)

        self._history = self._history[:MAX_HISTORY_ENTRIES]
        await self._save()
        return sent_count

    async def async_send_test(
        self,
        *,
        target_id: str | None = None,
        channel: NotificationChannel = NotificationChannel.MOBILE_PUSH,
    ) -> None:
        targets = [target for target in self._settings.targets if target.active]
        if target_id:
            targets = [target for target in targets if target.id == target_id]
        if channel == NotificationChannel.PERSISTENT:
            targets = [
                NotificationTarget(
                    id="persistent_notification",
                    service="notify.persistent_notification",
                    display_name="Home Assistant",
                    platform="ha",
                )
            ]

        if not targets:
            raise ValueError("No active target found for test notification")

        now = datetime.utcnow()
        for target in targets:
            message = NotificationMessage(
                id=str(uuid4()),
                event=create_notification_event(
                    "shopping_due",
                    title="Testbenachrichtigung",
                    message=f"Test an {target.display_name}",
                    payload={"click_url": "/lovelace/default_view"},
                    severity=NotificationSeverity.INFO,
                ),
                rule_id=None,
                target=target,
                channels=(channel,),
                title="Testbenachrichtigung",
                body=f"Test an {target.display_name} um {now.isoformat()}",
                severity=NotificationSeverity.INFO,
                click_url="/lovelace/default_view",
                dedup_key=f"test:{target.id}",
            )
            history_entry = await self._dispatcher.async_dispatch(message)
            self._history.insert(0, history_entry)

        self._history = self._history[:MAX_HISTORY_ENTRIES]
        await self._save()

    async def _save(self) -> None:
        await self._store.async_save(self._settings, self._history)


async def async_setup_notification_services(
    hass: HomeAssistant,
    manager: NotificationManager,
) -> None:
    """Register Home Assistant services for dashboard and automation usage."""

    async def _emit_event(call: ServiceCall) -> None:
        payload = dict(call.data)
        event_type = payload.pop("event_type")
        await manager.async_process_event(event_type, payload)

    async def _test_device(call: ServiceCall) -> None:
        await manager.async_send_test(
            target_id=call.data.get("target_id"),
            channel=NotificationChannel.MOBILE_PUSH,
        )

    async def _test_all(_call: ServiceCall) -> None:
        await manager.async_send_test(channel=NotificationChannel.MOBILE_PUSH)

    async def _test_persistent(_call: ServiceCall) -> None:
        await manager.async_send_test(channel=NotificationChannel.PERSISTENT)

    hass.services.async_register(DOMAIN, "notification_emit_event", _emit_event)
    hass.services.async_register(DOMAIN, "notification_test_device", _test_device)
    hass.services.async_register(DOMAIN, "notification_test_all", _test_all)
    hass.services.async_register(
        DOMAIN,
        "notification_test_persistent",
        _test_persistent,
    )


def _default_rule() -> NotificationRule:
    return NotificationRule(
        id="default_shopping_due",
        name="Shopping Reminder",
        enabled=True,
        event_types=("shopping_due", "low_stock_detected"),
        channels=(NotificationChannel.MOBILE_PUSH, NotificationChannel.PERSISTENT),
        severity=NotificationSeverity.WARNING,
        cooldown_seconds=900,
        conditions=(),
        message_template="${message}",
    )


def get_notification_manager(
    hass: HomeAssistant, entry_id: str
) -> NotificationManager | None:
    return hass.data.get(DOMAIN, {}).get(DATA_NOTIFICATION_MANAGER, {}).get(entry_id)
