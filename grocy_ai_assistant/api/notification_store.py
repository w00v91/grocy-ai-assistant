from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from grocy_ai_assistant.models.notification import (
    NotificationHistoryModel,
    NotificationOverviewResponse,
    NotificationRuleModel,
    NotificationSettingsModel,
    NotificationTargetModel,
)

DEFAULT_EVENT_TYPES = [
    "item_added",
    "item_removed",
    "item_checked",
    "item_unchecked",
    "shopping_due",
    "low_stock_detected",
    "recipe_missing_items",
]


class NotificationDashboardStore:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._lock = threading.Lock()

    def load(self) -> NotificationOverviewResponse:
        return self.load_for_user("default-user")

    def load_for_user(self, user_id: str) -> NotificationOverviewResponse:
        with self._lock:
            payload = self._load_payload()
            return self._overview_from_payload(payload, user_id)

    def save_overview(
        self, overview: NotificationOverviewResponse
    ) -> NotificationOverviewResponse:
        return self.save_overview_for_user("default-user", overview)

    def save_overview_for_user(
        self, user_id: str, overview: NotificationOverviewResponse
    ) -> NotificationOverviewResponse:
        with self._lock:
            payload = self._load_payload()
            user_bucket = self._ensure_user_bucket(payload, user_id)
            user_bucket["settings"] = overview.settings.model_dump()
            user_bucket["rules"] = [item.model_dump() for item in overview.rules]
            payload["devices"] = [item.model_dump() for item in overview.devices]
            payload["history"] = [item.model_dump() for item in overview.history[:300]]
            payload = {
                "version": payload.get("version", 2),
                "users": payload.get("users", {}),
                "devices": payload.get("devices", []),
                "history": payload.get("history", []),
            }
            self._write_payload(payload)
            return self._overview_from_payload(payload, user_id)

    def _load_payload(self) -> dict:
        if not self._storage_path.exists():
            return self._default_payload()
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return self._default_payload()
            return payload
        except (OSError, json.JSONDecodeError):
            return self._default_payload()

    def _write_payload(self, payload: dict) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _default_payload(self) -> dict:
        return {
            "version": 2,
            "users": {
                "default-user": {
                    "settings": NotificationSettingsModel(
                        enabled=True,
                        enabled_event_types=DEFAULT_EVENT_TYPES,
                        default_channels=["mobile_push"],
                        default_severity="info",
                    ).model_dump(),
                    "rules": self._default_rules_payload(),
                }
            },
            "devices": [],
            "history": [],
        }

    def _default_rules_payload(self) -> list[dict]:
        return [
            NotificationRuleModel(
                id="default-shopping-due",
                name="Einkauf fällig",
                event_types=["shopping_due"],
                channels=["mobile_push", "persistent_notification"],
                severity="warning",
                cooldown_seconds=900,
                message_template="${message}",
            ).model_dump(),
            NotificationRuleModel(
                id="default-low-stock",
                name="Niedriger Bestand",
                event_types=["low_stock_detected"],
                channels=["mobile_push"],
                severity="warning",
                cooldown_seconds=1800,
                message_template="⚠️ ${message}",
            ).model_dump(),
            NotificationRuleModel(
                id="default-recipe-missing",
                name="Fehlende Rezept-Zutaten",
                event_types=["recipe_missing_items"],
                channels=["persistent_notification"],
                severity="info",
                cooldown_seconds=3600,
                message_template="🍳 ${message}",
            ).model_dump(),
        ]

    def _ensure_user_bucket(self, payload: dict, user_id: str) -> dict:
        users = payload.setdefault("users", {})
        if user_id not in users or not isinstance(users[user_id], dict):
            users[user_id] = {
                "settings": NotificationSettingsModel(
                    enabled=True,
                    enabled_event_types=DEFAULT_EVENT_TYPES,
                    default_channels=["mobile_push"],
                    default_severity="info",
                ).model_dump(),
                "rules": self._default_rules_payload(),
            }
        users[user_id].setdefault("settings", NotificationSettingsModel().model_dump())
        users[user_id].setdefault("rules", self._default_rules_payload())
        return users[user_id]

    def _overview_from_payload(
        self, payload: dict, user_id: str
    ) -> NotificationOverviewResponse:
        if "users" not in payload:
            payload = {
                "version": 2,
                "users": {
                    "default-user": {
                        "settings": payload.get("settings")
                        or NotificationSettingsModel(
                            enabled=True,
                            enabled_event_types=DEFAULT_EVENT_TYPES,
                            default_channels=["mobile_push"],
                            default_severity="info",
                        ).model_dump(),
                        "rules": payload.get("rules") or self._default_rules_payload(),
                    }
                },
                "devices": payload.get("devices", []),
                "history": payload.get("history", []),
            }
        user_bucket = self._ensure_user_bucket(payload, user_id)
        settings = NotificationSettingsModel(**(user_bucket.get("settings") or {}))
        devices = [
            NotificationTargetModel(**item)
            for item in payload.get("devices", [])
            if isinstance(item, dict)
        ]
        rules = [
            NotificationRuleModel(**item)
            for item in user_bucket.get("rules", [])
            if isinstance(item, dict)
        ]
        history = [
            NotificationHistoryModel(**item)
            for item in payload.get("history", [])[:300]
            if isinstance(item, dict)
        ]
        return NotificationOverviewResponse(
            settings=settings,
            devices=devices,
            rules=rules,
            history=history,
        )


def create_history_entry(
    *,
    event_type: str,
    title: str,
    message: str,
    delivered: bool,
    target_id: str = "",
    channels: list[str] | None = None,
    rule_id: str = "",
    error: str = "",
) -> NotificationHistoryModel:
    return NotificationHistoryModel(
        id=str(uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        event_type=event_type,
        title=title,
        message=message,
        delivered=delivered,
        target_id=target_id,
        channels=channels or [],
        rule_id=rule_id,
        error=error,
    )
