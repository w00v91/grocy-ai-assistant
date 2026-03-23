"""Coordinator layer for the Grocy AI Assistant Home Assistant integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .addon_client import AddonClient
from .const import (
    CONF_API_BASE_URL,
    CONF_DASHBOARD_POLLING_INTERVAL_SECONDS,
    CONF_DEBUG_MODE,
    DASHBOARD_POLLING_DISABLED_INTERVAL_SECONDS,
    DEFAULT_ADDON_BASE_URL,
    DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS,
    DOMAIN,
    INTEGRATION_VERSION,
)
from .entity_payloads import (
    DEFAULT_EXPIRING_WITHIN_DAYS,
    build_expiring_stock_summary,
    build_recipe_summary,
    build_shopping_list_summary,
    build_stock_summary,
)
from .runtime import get_entry_data

_LOGGER = logging.getLogger(__name__)

DATA_ENTRY_CONFIG = "config"
DATA_COORDINATORS = "coordinators"

COORDINATOR_STATUS = "status"
COORDINATOR_INVENTORY = "inventory"
COORDINATOR_RECIPE_SUGGESTIONS = "recipe_suggestions"

CoordinatorPayload = dict[str, dict[str, Any]]


def _resolve_api_base_url(config: dict[str, Any]) -> str:
    return (
        config.get(CONF_API_BASE_URL)
        or config.get("addon_base_url")
        or DEFAULT_ADDON_BASE_URL
    )


def get_entry_coordinators(
    hass: HomeAssistant, entry_id: str
) -> dict[str, DataUpdateCoordinator]:
    coordinators = get_entry_data(hass, entry_id).get(DATA_COORDINATORS)
    if not isinstance(coordinators, dict):
        raise KeyError(f"Keine Coordinatoren für Entry {entry_id} gefunden")
    return coordinators


def _dashboard_update_interval(config: dict[str, Any]) -> timedelta | None:
    seconds = int(
        config.get(
            CONF_DASHBOARD_POLLING_INTERVAL_SECONDS,
            DEFAULT_DASHBOARD_POLLING_INTERVAL_SECONDS,
        )
    )
    if seconds <= DASHBOARD_POLLING_DISABLED_INTERVAL_SECONDS:
        return None
    return timedelta(seconds=max(1, seconds))


def _diagnostic_update_interval(config: dict[str, Any]) -> timedelta:
    dashboard_interval = _dashboard_update_interval(config)
    if dashboard_interval is None:
        return timedelta(seconds=30)
    return max(dashboard_interval, timedelta(seconds=30))


class GrocyAIBaseCoordinator(DataUpdateCoordinator[CoordinatorPayload]):
    """Shared coordinator base with centralized client and error handling."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        name: str,
        update_interval: timedelta | None,
    ) -> None:
        self.entry = entry
        self._debug_mode = bool(entry.options.get(CONF_DEBUG_MODE, False))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=name,
            update_interval=update_interval,
        )

    def _build_client(self) -> AddonClient:
        config = {**self.entry.data, **self.entry.options}
        return AddonClient(
            _resolve_api_base_url(config),
            config.get("api_key", ""),
            integration_version=INTEGRATION_VERSION,
        )

    async def _request_payload(
        self,
        *,
        label: str,
        request: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        try:
            payload = await request()
        except Exception as error:
            if self._debug_mode:
                _LOGGER.debug(
                    "Coordinator-Abfrage fehlgeschlagen (%s, %s): %s",
                    self.name,
                    label,
                    error,
                )
            raise UpdateFailed(f"{label}: {error}") from error

        http_status = payload.get("_http_status")
        if http_status != 200:
            detail = payload.get("detail") or f"HTTP {http_status}"
            raise UpdateFailed(f"{label}: {detail}")
        return payload


class GrocyAIStatusCoordinator(GrocyAIBaseCoordinator):
    """Coordinator for add-on status diagnostics."""

    async def _async_update_data(self) -> CoordinatorPayload:
        payload = await self._request_payload(
            label="Status",
            request=lambda: self._build_client().get_status(),
        )
        restart_required = bool(payload.get("homeassistant_restart_required", False))
        return {
            "status": {
                "state": "Online",
                "attributes": {
                    "addon_version": payload.get("addon_version", "unbekannt"),
                    "required_integration_version": payload.get(
                        "required_integration_version", "unbekannt"
                    ),
                    "homeassistant_restart_required": restart_required,
                },
            },
            "update_required": {
                "state": "Ja" if restart_required else "Nein",
                "attributes": {
                    "required_integration_version": payload.get(
                        "required_integration_version", "unbekannt"
                    ),
                    "current_integration_version": INTEGRATION_VERSION,
                    "reason": payload.get("update_reason", ""),
                },
            },
        }


class GrocyAIInventoryCoordinator(GrocyAIBaseCoordinator):
    """Coordinator for shopping list and stock data."""

    async def _async_update_data(self) -> CoordinatorPayload:
        client = self._build_client()
        shopping_payload, stock_payload = await asyncio.gather(
            self._request_payload(
                label="Einkaufsliste",
                request=lambda: client.get_shopping_list(),
            ),
            self._request_payload(
                label="Lager",
                request=lambda: client.get_stock_products(),
            ),
        )

        shopping_count, shopping_attributes = build_shopping_list_summary(
            shopping_payload.get("items") or []
        )
        stock_count, stock_attributes = build_stock_summary(
            stock_payload.get("items") or []
        )
        expiring_count, expiring_attributes = build_expiring_stock_summary(
            stock_payload.get("items") or [],
            expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
        )

        return {
            "shopping_list_open_count": {
                "state": shopping_count,
                "attributes": shopping_attributes,
            },
            "stock_products_total_count": {
                "state": stock_count,
                "attributes": stock_attributes,
            },
            "stock_products_expiring_count": {
                "state": expiring_count,
                "attributes": expiring_attributes,
            },
        }


class GrocyAIRecipeSuggestionsCoordinator(GrocyAIBaseCoordinator):
    """Coordinator for recipe suggestion sensor payloads."""

    async def _async_update_data(self) -> CoordinatorPayload:
        client = self._build_client()
        all_payload, expiring_payload = await asyncio.gather(
            self._request_payload(
                label="Rezeptvorschläge",
                request=lambda: client.get_recipe_suggestions(
                    soon_expiring_only=False,
                    expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
                ),
            ),
            self._request_payload(
                label="Rezeptvorschläge (bald ablaufend)",
                request=lambda: client.get_recipe_suggestions(
                    soon_expiring_only=True,
                    expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
                ),
            ),
        )

        top_ai_state, top_ai_attributes = build_recipe_summary(
            all_payload,
            soon_expiring_only=False,
            expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
            source="ai",
        )
        top_grocy_state, top_grocy_attributes = build_recipe_summary(
            all_payload,
            soon_expiring_only=False,
            expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
            source="grocy",
        )
        expiring_state, expiring_attributes = build_recipe_summary(
            expiring_payload,
            soon_expiring_only=True,
            expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
            source=None,
        )

        return {
            "recipe_suggestion_top_ai": {
                "state": top_ai_state,
                "attributes": top_ai_attributes,
            },
            "recipe_suggestion_top_grocy": {
                "state": top_grocy_state,
                "attributes": top_grocy_attributes,
            },
            "recipe_suggestion_expiring": {
                "state": expiring_state,
                "attributes": expiring_attributes,
            },
        }


async def async_setup_entry_coordinators(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, DataUpdateCoordinator]:
    """Create, refresh and store all entry-scoped coordinators."""

    config = {**entry.data, **entry.options}
    coordinators: dict[str, DataUpdateCoordinator] = {
        COORDINATOR_STATUS: GrocyAIStatusCoordinator(
            hass,
            entry,
            name=f"{DOMAIN}-{entry.entry_id}-status",
            update_interval=_diagnostic_update_interval(config),
        ),
        COORDINATOR_INVENTORY: GrocyAIInventoryCoordinator(
            hass,
            entry,
            name=f"{DOMAIN}-{entry.entry_id}-inventory",
            update_interval=_dashboard_update_interval(config),
        ),
        COORDINATOR_RECIPE_SUGGESTIONS: GrocyAIRecipeSuggestionsCoordinator(
            hass,
            entry,
            name=f"{DOMAIN}-{entry.entry_id}-recipes",
            update_interval=_dashboard_update_interval(config),
        ),
    }

    await asyncio.gather(
        *(coordinator.async_refresh() for coordinator in coordinators.values())
    )

    entry_data = get_entry_data(hass, entry.entry_id)
    entry_data[DATA_COORDINATORS] = coordinators
    return coordinators
