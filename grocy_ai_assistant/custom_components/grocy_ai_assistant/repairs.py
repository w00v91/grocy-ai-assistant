"""Issue-registry based repairs for config entry health states."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from .const import DOMAIN

_HOMEASSISTANT_DOMAIN = "homeassistant"
_HOMEASSISTANT_RESTART_SERVICE = "restart"

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
            is_fixable=True,
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


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> Any:
    """Create repair flows for Grocy AI Assistant issues."""

    if not issue_id.endswith(f"_{_RESTART_REQUIRED_SUFFIX}"):
        raise ValueError(f"Unsupported repair issue: {issue_id}")

    from homeassistant.components.repairs import RepairsFlow

    class RestartHomeAssistantRepairFlow(RepairsFlow):
        """Repair flow that offers Home Assistant's restart action."""

        async def async_step_init(
            self, user_input: dict[str, str] | None = None
        ) -> Any:
            """Handle the first step of the restart repair flow."""

            return await self.async_step_confirm(user_input)

        async def async_step_confirm(
            self, user_input: dict[str, str] | None = None
        ) -> Any:
            """Confirm and trigger the standard Home Assistant restart action."""

            if user_input is not None:
                await self.hass.services.async_call(
                    _HOMEASSISTANT_DOMAIN,
                    _HOMEASSISTANT_RESTART_SERVICE,
                    {},
                    blocking=False,
                )
                return self.async_create_entry(title="", data={})

            return self.async_show_form(step_id="confirm")

    return RestartHomeAssistantRepairFlow()
