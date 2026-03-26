import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import (
    COORDINATOR_INVENTORY,
    COORDINATOR_RECIPE_SUGGESTIONS,
    COORDINATOR_STATUS,
    get_entry_coordinators,
)
from .entity import build_device_info
from .runtime_state import (
    RUNTIME_ANALYSIS_STATUS,
    RUNTIME_BARCODE_STATUS,
    RUNTIME_LLAVA_STATUS,
    RUNTIME_RESPONSE,
    RUNTIME_RESPONSE_TIMING,
    DEFAULT_RESPONSE_PAYLOAD,
    DEFAULT_RESPONSE_TIMING,
    DEFAULT_STATUS_PAYLOAD,
    dispatcher_signal,
    get_response_timing,
    get_runtime_payload,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors for a config entry."""
    coordinators = get_entry_coordinators(hass, entry.entry_id)
    async_add_entities(
        [
            GrocyAISensor(entry, coordinators[COORDINATOR_STATUS]),
            GrocyAIResponseSensor(entry),
            GrocyAIUpdateRequiredSensor(entry, coordinators[COORDINATOR_STATUS]),
            GrocyAILastResponseTimeSensor(entry),
            GrocyAIAverageResponseTimeSensor(entry),
            GrocyAIShoppingListOpenCountSensor(
                entry, coordinators[COORDINATOR_INVENTORY]
            ),
            GrocyAIStockProductCountSensor(entry, coordinators[COORDINATOR_INVENTORY]),
            GrocyAIExpiringStockProductCountSensor(
                entry, coordinators[COORDINATOR_INVENTORY]
            ),
            GrocyAITopAIRecipeSuggestionSensor(
                entry, coordinators[COORDINATOR_RECIPE_SUGGESTIONS]
            ),
            GrocyAITopGrocyRecipeSuggestionSensor(
                entry, coordinators[COORDINATOR_RECIPE_SUGGESTIONS]
            ),
            GrocyAISoonExpiringRecipeSuggestionSensor(
                entry, coordinators[COORDINATOR_RECIPE_SUGGESTIONS]
            ),
            GrocyAIAnalysisStatusSensor(entry),
            GrocyAIBarcodeLookupStatusSensor(entry),
            GrocyAILlavaScanStatusSensor(entry),
        ]
    )


class _BaseAddonSensor(SensorEntity):
    def __init__(self, entry, *, translation_key: str):
        self._entry = entry
        self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):
        return build_device_info(self._entry.entry_id, getattr(self, "hass", None))


class _CoordinatorAddonSensor(CoordinatorEntity, _BaseAddonSensor):
    def __init__(
        self,
        entry,
        coordinator,
        *,
        translation_key: str,
        data_key: str,
        fallback_native_value,
    ):
        _BaseAddonSensor.__init__(self, entry, translation_key=translation_key)
        CoordinatorEntity.__init__(self, coordinator)
        self._data_key = data_key
        self._fallback_native_value = fallback_native_value

    def _payload(self) -> dict:
        data = self.coordinator.data or {}
        payload = data.get(self._data_key)
        return payload if isinstance(payload, dict) else {}

    @property
    def native_value(self):
        return self._payload().get("state", self._fallback_native_value)

    @property
    def extra_state_attributes(self):
        attributes = dict(self._payload().get("attributes") or {})
        attributes["last_update_success"] = self.coordinator.last_update_success
        if self.coordinator.last_exception is not None:
            attributes["last_error"] = str(self.coordinator.last_exception)
        else:
            attributes.pop("last_error", None)
        return attributes


class _RuntimePayloadSensor(_BaseAddonSensor):
    def __init__(
        self,
        entry,
        *,
        translation_key: str,
        unique_suffix: str,
        runtime_key: str,
        icon: str,
        default_payload: dict[str, Any],
    ):
        super().__init__(entry, translation_key=translation_key)
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._runtime_key = runtime_key
        self._default_payload = default_payload
        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _payload(self) -> dict[str, Any]:
        if self.hass is None:
            return dict(self._default_payload)

        payload = get_runtime_payload(
            self.hass, self._entry.entry_id, self._runtime_key
        )
        return payload or dict(self._default_payload)

    async def async_added_to_hass(self):
        signal = dispatcher_signal(self._entry.entry_id, self._runtime_key)
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_runtime_update)
        )

    @callback
    def _handle_runtime_update(self, _payload: dict[str, Any]) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._payload().get("state", self._default_payload.get("state"))

    @property
    def extra_state_attributes(self):
        return dict(self._payload().get("attributes") or {})

    @property
    def icon(self):
        return str(self.extra_state_attributes.get("icon") or self._attr_icon)


class _RuntimeTimingSensor(_BaseAddonSensor):
    def __init__(
        self,
        entry,
        *,
        translation_key: str,
        unique_suffix: str,
        state_key: str,
        icon: str,
    ):
        super().__init__(entry, translation_key=translation_key)
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._state_key = state_key
        self._attr_native_unit_of_measurement = "ms"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _timing(self) -> dict[str, Any]:
        if self.hass is None:
            return dict(DEFAULT_RESPONSE_TIMING)
        return get_response_timing(self.hass, self._entry.entry_id)

    async def async_added_to_hass(self):
        signal = dispatcher_signal(self._entry.entry_id, RUNTIME_RESPONSE_TIMING)
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_runtime_update)
        )

    @callback
    def _handle_runtime_update(self, _payload: dict[str, Any]) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._timing().get(self._state_key)

    @property
    def extra_state_attributes(self):
        timing = self._timing()
        return {"requests_count": int(timing.get("count", 0))}


class GrocyAISensor(_CoordinatorAddonSensor):
    """Sensor for add-on availability."""

    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            translation_key="status",
            data_key="status",
            fallback_native_value="offline",
        )
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_icon = "mdi:robot"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class GrocyAIUpdateRequiredSensor(_CoordinatorAddonSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            translation_key="home_assistant_update_required",
            data_key="update_required",
            fallback_native_value="unknown",
        )
        self._attr_unique_id = f"{entry.entry_id}_ha_update_required"
        self._attr_icon = "mdi:update"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class GrocyAIResponseSensor(_RuntimePayloadSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="response_text",
            unique_suffix="response_text",
            runtime_key=RUNTIME_RESPONSE,
            icon="mdi:comment-text-outline",
            default_payload=DEFAULT_RESPONSE_PAYLOAD,
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        _LOGGER.info("Response sensor registered and ready")


class GrocyAILastResponseTimeSensor(_RuntimeTimingSensor):
    """Diagnostic sensor containing the duration of the latest AI request."""

    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="ai_response_time_last",
            unique_suffix="ai_response_time_last_ms",
            state_key="last_ms",
            icon="mdi:timer-outline",
        )


class GrocyAIAverageResponseTimeSensor(_RuntimeTimingSensor):
    """Diagnostic sensor containing the average duration of AI requests."""

    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="ai_response_time_average",
            unique_suffix="ai_response_time_avg_ms",
            state_key="average_ms",
            icon="mdi:chart-line",
        )


class GrocyAIShoppingListOpenCountSensor(_CoordinatorAddonSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            translation_key="shopping_list_open_count",
            data_key="shopping_list_open_count",
            fallback_native_value=0,
        )
        self._attr_unique_id = f"{entry.entry_id}_shopping_list_open_count"
        self._attr_icon = "mdi:cart-outline"


class GrocyAIStockProductCountSensor(_CoordinatorAddonSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            translation_key="stock_products_total_count",
            data_key="stock_products_total_count",
            fallback_native_value=0,
        )
        self._attr_unique_id = f"{entry.entry_id}_stock_products_total_count"
        self._attr_icon = "mdi:fridge-outline"


class GrocyAIExpiringStockProductCountSensor(_CoordinatorAddonSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            translation_key="stock_products_expiring_count",
            data_key="stock_products_expiring_count",
            fallback_native_value=0,
        )
        self._attr_unique_id = f"{entry.entry_id}_stock_products_expiring_count"
        self._attr_icon = "mdi:calendar-alert-outline"


class _RecipeSuggestionSensor(_CoordinatorAddonSensor):
    def __init__(
        self,
        entry,
        coordinator,
        *,
        translation_key: str,
        suffix: str,
    ):
        super().__init__(
            entry,
            coordinator,
            translation_key=translation_key,
            data_key=suffix,
            fallback_native_value="none",
        )
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_icon = "mdi:chef-hat"


class GrocyAITopAIRecipeSuggestionSensor(_RecipeSuggestionSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            translation_key="recipe_suggestion_top_ai",
            suffix="recipe_suggestion_top_ai",
        )


class GrocyAITopGrocyRecipeSuggestionSensor(_RecipeSuggestionSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            translation_key="recipe_suggestion_top_grocy",
            suffix="recipe_suggestion_top_grocy",
        )


class GrocyAISoonExpiringRecipeSuggestionSensor(_RecipeSuggestionSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            translation_key="recipe_suggestion_expiring",
            suffix="recipe_suggestion_expiring",
        )


class GrocyAIAnalysisStatusSensor(_RuntimePayloadSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="analysis_status",
            unique_suffix="analysis_status",
            runtime_key=RUNTIME_ANALYSIS_STATUS,
            icon="mdi:robot-outline",
            default_payload=DEFAULT_STATUS_PAYLOAD,
        )


class GrocyAIBarcodeLookupStatusSensor(_RuntimePayloadSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="barcode_lookup_status",
            unique_suffix="barcode_lookup_status",
            runtime_key=RUNTIME_BARCODE_STATUS,
            icon="mdi:barcode-scan",
            default_payload=DEFAULT_STATUS_PAYLOAD,
        )


class GrocyAILlavaScanStatusSensor(_RuntimePayloadSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="llava_scan_status",
            unique_suffix="llava_scan_status",
            runtime_key=RUNTIME_LLAVA_STATUS,
            icon="mdi:image-search-outline",
            default_payload=DEFAULT_STATUS_PAYLOAD,
        )
