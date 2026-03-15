"""Rule engine for transforming domain events into delivery messages."""

from __future__ import annotations

from datetime import datetime
from string import Template
from typing import Any
from uuid import uuid4

from .notify_models import (
    NotificationChannel,
    NotificationEvent,
    NotificationMessage,
    NotificationRule,
    NotificationSettings,
    NotificationTarget,
    QuietHours,
    RuleCondition,
)


class NotificationRuleEngine:
    """Evaluates rules with cooldown, quiet hours and declarative conditions."""

    def __init__(self) -> None:
        self._last_sent_by_key: dict[str, datetime] = {}

    def evaluate(
        self,
        event: NotificationEvent,
        settings: NotificationSettings,
    ) -> list[NotificationMessage]:
        if not settings.preferences.enabled:
            return []

        if (
            settings.enabled_event_types
            and event.event_type not in settings.enabled_event_types
        ):
            return []

        messages: list[NotificationMessage] = []
        default_targets = [target for target in settings.targets if target.active]

        for rule in settings.rules:
            if not self._matches_event(rule, event):
                continue
            if not self._matches_conditions(rule.conditions, event.payload):
                continue
            if self._is_in_quiet_hours(rule.quiet_hours, event.created_at):
                continue

            channels = rule.channels or settings.preferences.default_channels
            mobile_channels = tuple(
                channel
                for channel in channels
                if channel == NotificationChannel.MOBILE_PUSH
            )
            persistent_enabled = NotificationChannel.PERSISTENT in channels

            targets = self._resolve_targets(rule, settings.targets, default_targets)
            if mobile_channels and not targets:
                continue

            for target in targets:
                if not mobile_channels:
                    continue
                dedup_key = f"{rule.id}:{event.event_type}:{target.id}:{','.join(ch.value for ch in channels)}"
                if self._is_on_cooldown(rule, dedup_key, event.created_at):
                    continue

                message = NotificationMessage(
                    id=str(uuid4()),
                    event=event,
                    rule_id=rule.id,
                    target=target,
                    channels=mobile_channels,
                    title=event.title,
                    body=_render_message(rule, event),
                    severity=rule.severity or event.severity,
                    click_url=event.payload.get("click_url"),
                    dedup_key=dedup_key,
                    mobile_data={
                        "tag": event.payload.get("tag", f"grocy-{event.event_type}"),
                        "group": event.payload.get("group", "grocy-shopping"),
                        "url": event.payload.get("click_url", "/lovelace/default_view"),
                    },
                )
                messages.append(message)
                self._last_sent_by_key[dedup_key] = event.created_at

            if persistent_enabled:
                persistent_target = NotificationTarget(
                    id="persistent_notification",
                    service="persistent_notification.create",
                    display_name="Home Assistant",
                    platform="ha",
                    active=True,
                )
                dedup_key = f"{rule.id}:{event.event_type}:{persistent_target.id}:{NotificationChannel.PERSISTENT.value}"
                if self._is_on_cooldown(rule, dedup_key, event.created_at):
                    continue

                messages.append(
                    NotificationMessage(
                        id=str(uuid4()),
                        event=event,
                        rule_id=rule.id,
                        target=persistent_target,
                        channels=(NotificationChannel.PERSISTENT,),
                        title=event.title,
                        body=_render_message(rule, event),
                        severity=rule.severity or event.severity,
                        click_url=event.payload.get("click_url"),
                        dedup_key=dedup_key,
                        mobile_data={
                            "tag": event.payload.get(
                                "tag", f"grocy-{event.event_type}"
                            ),
                            "group": event.payload.get("group", "grocy-shopping"),
                            "url": event.payload.get(
                                "click_url", "/lovelace/default_view"
                            ),
                        },
                    )
                )
                self._last_sent_by_key[dedup_key] = event.created_at

        return messages

    def _matches_event(self, rule: NotificationRule, event: NotificationEvent) -> bool:
        return rule.enabled and event.event_type in rule.event_types

    def _resolve_targets(
        self,
        rule: NotificationRule,
        configured_targets: list[NotificationTarget],
        default_targets: list[NotificationTarget],
    ) -> list[NotificationTarget]:
        if not rule.target_device_ids and not rule.target_user_ids:
            return default_targets

        targets = []
        for target in configured_targets:
            if not target.active:
                continue
            if rule.target_device_ids and target.id not in rule.target_device_ids:
                continue
            if rule.target_user_ids and target.user_id not in rule.target_user_ids:
                continue
            targets.append(target)
        return targets

    def _is_in_quiet_hours(self, quiet_hours: QuietHours | None, now: datetime) -> bool:
        if quiet_hours is None:
            return False

        current = now.time()
        start = quiet_hours.start
        end = quiet_hours.end
        if start <= end:
            return start <= current <= end
        return current >= start or current <= end

    def _is_on_cooldown(
        self, rule: NotificationRule, dedup_key: str, now: datetime
    ) -> bool:
        if rule.cooldown_seconds <= 0:
            return False
        last_sent = self._last_sent_by_key.get(dedup_key)
        if last_sent is None:
            return False
        return (now - last_sent).total_seconds() < rule.cooldown_seconds

    def _matches_conditions(
        self, conditions: tuple[RuleCondition, ...], payload: dict[str, Any]
    ) -> bool:
        for condition in conditions:
            actual = payload.get(condition.key)
            if not _compare_values(actual, condition.operator, condition.value):
                return False
        return True


def _render_message(rule: NotificationRule, event: NotificationEvent) -> str:
    if not rule.message_template:
        return event.message

    template_data = {
        "event_type": event.event_type,
        "title": event.title,
        "message": event.message,
        **event.payload,
    }
    return Template(rule.message_template).safe_substitute(template_data)


def _compare_values(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "lt":
        return actual is not None and actual < expected
    if operator == "lte":
        return actual is not None and actual <= expected
    if operator == "contains":
        return actual is not None and expected in actual
    return False
