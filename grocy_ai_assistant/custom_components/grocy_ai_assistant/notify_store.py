"""Persistent storage for notification settings and history."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .notify_models import (
    NotificationChannel,
    NotificationHistoryEntry,
    NotificationPreference,
    NotificationRule,
    NotificationSettings,
    NotificationSeverity,
    NotificationTarget,
    QuietHours,
    RuleCondition,
)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.notifications"
MAX_HISTORY_ENTRIES = 500


class NotificationStore:
    """Store wrapper with migration-ready schema handling."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry_id}")

    async def async_load(
        self,
    ) -> tuple[NotificationSettings, list[NotificationHistoryEntry]]:
        data = await self._store.async_load() or {}
        settings = _deserialize_settings(data.get("settings") or {})
        history = [
            _deserialize_history_entry(item)
            for item in data.get("history", [])[:MAX_HISTORY_ENTRIES]
        ]
        return settings, history

    async def async_save(
        self,
        settings: NotificationSettings,
        history: list[NotificationHistoryEntry],
    ) -> None:
        payload = {
            "settings": _serialize_settings(settings),
            "history": [
                _serialize_history_entry(item) for item in history[:MAX_HISTORY_ENTRIES]
            ],
        }
        await self._store.async_save(payload)


def _serialize_settings(settings: NotificationSettings) -> dict[str, Any]:
    return {
        "preferences": {
            "enabled": settings.preferences.enabled,
            "default_channels": [
                channel.value for channel in settings.preferences.default_channels
            ],
            "default_severity": settings.preferences.default_severity.value,
        },
        "enabled_event_types": list(settings.enabled_event_types),
        "targets": [
            {
                "id": target.id,
                "service": target.service,
                "display_name": target.display_name,
                "platform": target.platform,
                "user_id": target.user_id,
                "active": target.active,
            }
            for target in settings.targets
        ],
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "enabled": rule.enabled,
                "event_types": list(rule.event_types),
                "target_user_ids": list(rule.target_user_ids),
                "target_device_ids": list(rule.target_device_ids),
                "channels": [channel.value for channel in rule.channels],
                "severity": rule.severity.value,
                "cooldown_seconds": rule.cooldown_seconds,
                "quiet_hours": (
                    {
                        "start": rule.quiet_hours.start.isoformat(),
                        "end": rule.quiet_hours.end.isoformat(),
                        "timezone": rule.quiet_hours.timezone,
                    }
                    if rule.quiet_hours
                    else None
                ),
                "conditions": [
                    {
                        "key": condition.key,
                        "operator": condition.operator,
                        "value": condition.value,
                    }
                    for condition in rule.conditions
                ],
                "message_template": rule.message_template,
            }
            for rule in settings.rules
        ],
    }


def _deserialize_settings(payload: dict[str, Any]) -> NotificationSettings:
    pref = payload.get("preferences") or {}
    preferences = NotificationPreference(
        enabled=bool(pref.get("enabled", True)),
        default_channels=tuple(
            NotificationChannel(value)
            for value in pref.get(
                "default_channels", [NotificationChannel.MOBILE_PUSH.value]
            )
        ),
        default_severity=NotificationSeverity(
            pref.get("default_severity", NotificationSeverity.INFO.value)
        ),
    )

    targets = [
        NotificationTarget(
            id=item["id"],
            service=item["service"],
            display_name=item.get("display_name", item["service"]),
            platform=item.get("platform", "unknown"),
            user_id=item.get("user_id"),
            active=bool(item.get("active", True)),
        )
        for item in payload.get("targets", [])
        if item.get("id") and item.get("service")
    ]

    rules = []
    for item in payload.get("rules", []):
        quiet_hours_payload = item.get("quiet_hours")
        quiet_hours = None
        if quiet_hours_payload:
            quiet_hours = QuietHours(
                start=_parse_time(quiet_hours_payload.get("start", "22:00:00")),
                end=_parse_time(quiet_hours_payload.get("end", "07:00:00")),
                timezone=quiet_hours_payload.get("timezone", "local"),
            )

        rules.append(
            NotificationRule(
                id=item["id"],
                name=item.get("name", item["id"]),
                enabled=bool(item.get("enabled", True)),
                event_types=tuple(item.get("event_types", [])),
                target_user_ids=tuple(item.get("target_user_ids", [])),
                target_device_ids=tuple(item.get("target_device_ids", [])),
                channels=tuple(
                    NotificationChannel(value) for value in item.get("channels", [])
                ),
                severity=NotificationSeverity(
                    item.get("severity", NotificationSeverity.INFO.value)
                ),
                cooldown_seconds=int(item.get("cooldown_seconds", 0) or 0),
                quiet_hours=quiet_hours,
                conditions=tuple(
                    RuleCondition(
                        key=condition["key"],
                        operator=condition.get("operator", "eq"),
                        value=condition.get("value"),
                    )
                    for condition in item.get("conditions", [])
                    if condition.get("key")
                ),
                message_template=item.get("message_template"),
            )
        )

    return NotificationSettings(
        preferences=preferences,
        targets=targets,
        rules=rules,
        enabled_event_types=tuple(payload.get("enabled_event_types", [])),
    )


def _serialize_history_entry(entry: NotificationHistoryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "message_id": entry.message_id,
        "event_type": entry.event_type,
        "rule_id": entry.rule_id,
        "target_id": entry.target_id,
        "channels": [channel.value for channel in entry.channels],
        "delivered": entry.delivered,
        "delivered_channels": [channel.value for channel in entry.delivered_channels],
        "error": entry.error,
        "created_at": entry.created_at.isoformat(),
    }


def _deserialize_history_entry(payload: dict[str, Any]) -> NotificationHistoryEntry:
    return NotificationHistoryEntry(
        id=payload["id"],
        message_id=payload["message_id"],
        event_type=payload["event_type"],
        rule_id=payload.get("rule_id"),
        target_id=payload.get("target_id", "unknown"),
        channels=tuple(
            NotificationChannel(value) for value in payload.get("channels", [])
        ),
        delivered=bool(payload.get("delivered", False)),
        delivered_channels=tuple(
            NotificationChannel(value)
            for value in payload.get("delivered_channels", [])
        ),
        error=payload.get("error"),
        created_at=_parse_datetime(payload.get("created_at")),
    )


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_time(value: str) -> time:
    return time.fromisoformat(value)
