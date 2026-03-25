"""Issue-registry based repairs for config entry health states."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from .const import DOMAIN

_RESTART_REQUIRED_SUFFIX = "restart_required"
_ADDON_UNREACHABLE_SUFFIX = "addon_unreachable"
_INVALID_AUTH_SUFFIX = "invalid_auth"


def _issue_id(entry_id: str, suffix: str) -> str:
    return f"{entry_id}_{suffix}"


def _issue_registry():
    try:
        from homeassistant.helpers import issue_registry as issue_registry
    except ImportError:
        return None
    return issue_registry


async def async_sync_repairs_for_entry(
    hass: HomeAssistant,
    entry_id: str,
    status_payload: dict[str, Any],
) -> None:
    """Sync issue registry entries to current status and coordinator health."""

    issue_registry = _issue_registry()
    if issue_registry is None:
        return

    restart_required = bool(status_payload.get("homeassistant_restart_required", False))
    update_success = bool(status_payload.get("last_update_success", True))
    last_exception = status_payload.get("last_exception")
    last_exception_text = str(last_exception).lower() if last_exception else ""
    invalid_auth = (not update_success) and any(
        marker in last_exception_text for marker in ("401", "unauthorized", "forbidden")
    )
    addon_unreachable = not update_success and bool(last_exception) and not invalid_auth

    restart_issue_id = _issue_id(entry_id, _RESTART_REQUIRED_SUFFIX)
    if restart_required:
        issue_registry.async_create_issue(
            hass,
            DOMAIN,
            restart_issue_id,
            is_fixable=False,
            severity=issue_registry.IssueSeverity.WARNING,
            translation_key="restart_required",
        )
    else:
        issue_registry.async_delete_issue(hass, DOMAIN, restart_issue_id)

    unreachable_issue_id = _issue_id(entry_id, _ADDON_UNREACHABLE_SUFFIX)
    if addon_unreachable:
        issue_registry.async_create_issue(
            hass,
            DOMAIN,
            unreachable_issue_id,
            is_fixable=False,
            severity=issue_registry.IssueSeverity.ERROR,
            translation_key="addon_unreachable",
        )
    else:
        issue_registry.async_delete_issue(hass, DOMAIN, unreachable_issue_id)

    invalid_auth_issue_id = _issue_id(entry_id, _INVALID_AUTH_SUFFIX)
    if invalid_auth:
        issue_registry.async_create_issue(
            hass,
            DOMAIN,
            invalid_auth_issue_id,
            is_fixable=False,
            severity=issue_registry.IssueSeverity.ERROR,
            translation_key="invalid_auth",
        )
    else:
        issue_registry.async_delete_issue(hass, DOMAIN, invalid_auth_issue_id)


async def async_clear_repairs_for_entry(hass: HomeAssistant, entry_id: str) -> None:
    """Clear all repairs owned by a config entry."""

    issue_registry = _issue_registry()
    if issue_registry is None:
        return

    issue_registry.async_delete_issue(
        hass, DOMAIN, _issue_id(entry_id, _RESTART_REQUIRED_SUFFIX)
    )
    issue_registry.async_delete_issue(
        hass, DOMAIN, _issue_id(entry_id, _ADDON_UNREACHABLE_SUFFIX)
    )
    issue_registry.async_delete_issue(
        hass, DOMAIN, _issue_id(entry_id, _INVALID_AUTH_SUFFIX)
    )
