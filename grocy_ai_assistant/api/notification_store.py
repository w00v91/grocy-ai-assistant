from __future__ import annotations

import json
import threading
from datetime import datetime
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
        with self._lock:
            payload = self._load_payload()
            return self._overview_from_payload(payload)

    def save_overview(
        self, overview: NotificationOverviewResponse
    ) -> NotificationOverviewResponse:
        with self._lock:
            payload = {
                "version": 1,
                "settings": overview.settings.model_dump(),
                "devices": [item.model_dump() for item in overview.devices],
                "rules": [item.model_dump() for item in overview.rules],
                "history": [item.model_dump() for item in overview.history[:300]],
            }
            self._write_payload(payload)
            return self._overview_from_payload(payload)

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
            "version": 1,
            "settings": NotificationSettingsModel(
                enabled=True,
                enabled_event_types=DEFAULT_EVENT_TYPES,
                default_channels=["mobile_push"],
                default_severity="info",
            ).model_dump(),
            "devices": [],
            "rules": [
                NotificationRuleModel(
                    id="default-shopping-due",
                    name="Standard Einkaufserinnerung",
                    event_types=["shopping_due", "low_stock_detected"],
                    channels=["mobile_push", "persistent_notification"],
                    severity="warning",
                    cooldown_seconds=900,
                    message_template="${message}",
                ).model_dump()
            ],
            "history": [],
        }

    def _overview_from_payload(self, payload: dict) -> NotificationOverviewResponse:
        settings = NotificationSettingsModel(**(payload.get("settings") or {}))
        devices = [
            NotificationTargetModel(**item)
            for item in payload.get("devices", [])
            if isinstance(item, dict)
        ]
        rules = [
            NotificationRuleModel(**item)
            for item in payload.get("rules", [])
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
        created_at=datetime.utcnow().isoformat(),
        event_type=event_type,
        title=title,
        message=message,
        delivered=delivered,
        target_id=target_id,
        channels=channels or [],
        rule_id=rule_id,
        error=error,
    )
