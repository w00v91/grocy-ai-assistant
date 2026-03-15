"""Notification dispatcher translating NotificationMessage into HA service calls."""

from __future__ import annotations

import logging
from uuid import uuid4

from homeassistant.core import HomeAssistant

from .notify_models import (
    NotificationChannel,
    NotificationHistoryEntry,
    NotificationMessage,
    NotificationSeverity,
)

_LOGGER = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches messages to Home Assistant channels."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def async_dispatch(
        self, message: NotificationMessage
    ) -> NotificationHistoryEntry:
        delivered_channels: list[NotificationChannel] = []
        errors: list[str] = []

        for channel in message.channels:
            try:
                if channel == NotificationChannel.MOBILE_PUSH:
                    await self._send_mobile_push(message)
                elif channel == NotificationChannel.PERSISTENT:
                    await self._send_persistent_notification(message)
                else:
                    raise ValueError(f"Unsupported channel: {channel}")
                delivered_channels.append(channel)
            except Exception as err:  # pragma: no cover - defensive logging
                _LOGGER.exception("Failed to dispatch %s via %s", message.id, channel)
                errors.append(str(err))

        return NotificationHistoryEntry(
            id=str(uuid4()),
            message_id=message.id,
            event_type=message.event.event_type,
            rule_id=message.rule_id,
            target_id=message.target.id,
            channels=message.channels,
            delivered=bool(delivered_channels),
            delivered_channels=tuple(delivered_channels),
            error="; ".join(errors) if errors else None,
        )

    async def _send_mobile_push(self, message: NotificationMessage) -> None:
        domain, service = message.target.service.split(".", 1)
        service_data = {
            "title": message.title,
            "message": message.body,
            "data": {
                **message.mobile_data,
                "tag": message.dedup_key or message.mobile_data.get("tag"),
                "clickAction": message.click_url or message.mobile_data.get("url"),
                "url": message.click_url or message.mobile_data.get("url"),
                "priority": _severity_to_mobile_priority(message.severity),
                "ttl": 0 if message.severity == NotificationSeverity.CRITICAL else 300,
            },
        }
        await self._hass.services.async_call(
            domain,
            service,
            service_data,
            blocking=True,
        )

    async def _send_persistent_notification(self, message: NotificationMessage) -> None:
        service_data = {
            "title": message.title,
            "message": message.body,
            "notification_id": message.dedup_key or message.id,
        }

        services = self._hass.services.async_services()
        persistent_available = "create" in services.get("persistent_notification", {})

        if persistent_available:
            await self._hass.services.async_call(
                "persistent_notification",
                "create",
                service_data,
                blocking=True,
            )
            return

        # Fallback for setups exposing persistent notifications via notify service.
        await self._hass.services.async_call(
            "notify",
            "persistent_notification",
            service_data,
            blocking=True,
        )


def _severity_to_mobile_priority(severity: NotificationSeverity) -> str:
    if severity == NotificationSeverity.CRITICAL:
        return "high"
    if severity == NotificationSeverity.WARNING:
        return "default"
    return "low"
