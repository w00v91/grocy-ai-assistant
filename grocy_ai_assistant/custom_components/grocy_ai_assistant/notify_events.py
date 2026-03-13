"""Notification event definitions and helpers."""

from __future__ import annotations

from .notify_models import NotificationEvent, NotificationSeverity

EVENT_ITEM_ADDED = "item_added"
EVENT_ITEM_REMOVED = "item_removed"
EVENT_ITEM_CHECKED = "item_checked"
EVENT_ITEM_UNCHECKED = "item_unchecked"
EVENT_SHOPPING_DUE = "shopping_due"
EVENT_LOW_STOCK_DETECTED = "low_stock_detected"
EVENT_RECIPE_MISSING_ITEMS = "recipe_missing_items"

SUPPORTED_NOTIFICATION_EVENTS: tuple[str, ...] = (
    EVENT_ITEM_ADDED,
    EVENT_ITEM_REMOVED,
    EVENT_ITEM_CHECKED,
    EVENT_ITEM_UNCHECKED,
    EVENT_SHOPPING_DUE,
    EVENT_LOW_STOCK_DETECTED,
    EVENT_RECIPE_MISSING_ITEMS,
)


def create_notification_event(
    event_type: str,
    *,
    title: str,
    message: str,
    payload: dict | None = None,
    severity: NotificationSeverity = NotificationSeverity.INFO,
    source: str = "shopping",
) -> NotificationEvent:
    """Create a canonical domain event for the notification pipeline."""
    return NotificationEvent(
        event_type=event_type,
        title=title,
        message=message,
        payload=payload or {},
        severity=severity,
        source=source,
    )
