import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import (
    COORDINATOR_INVENTORY,
    COORDINATOR_RECIPE_SUGGESTIONS,
    COORDINATOR_STATUS,
    get_entry_coordinators,
)
from .entity import build_device_info

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
        return build_device_info(self._entry.entry_id)


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


class _StaticStatusSensor(_BaseAddonSensor):
    def __init__(
        self,
        entry,
        *,
        translation_key: str,
        unique_suffix: str,
        icon: str,
        default_native_value: str = "ready",
    ):
        super().__init__(entry, translation_key=translation_key)
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_native_value = default_native_value
        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class GrocyAIResponseSensor(_StaticStatusSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="response_text",
            unique_suffix="response_text",
            icon="mdi:comment-text-outline",
        )

    async def async_added_to_hass(self):
        _LOGGER.info("Response sensor registered and ready")


class GrocyAILastResponseTimeSensor(_BaseAddonSensor):
    """Diagnostic sensor containing the duration of the latest AI request."""

    def __init__(self, entry):
        super().__init__(entry, translation_key="ai_response_time_last")
        self._attr_unique_id = f"{entry.entry_id}_ai_response_time_last_ms"
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = "ms"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:timer-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class GrocyAIAverageResponseTimeSensor(_BaseAddonSensor):
    """Diagnostic sensor containing the average duration of AI requests."""

    def __init__(self, entry):
        super().__init__(entry, translation_key="ai_response_time_average")
        self._attr_unique_id = f"{entry.entry_id}_ai_response_time_avg_ms"
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = "ms"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:chart-line"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


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


class GrocyAIAnalysisStatusSensor(_StaticStatusSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="analysis_status",
            unique_suffix="analysis_status",
            icon="mdi:robot-outline",
        )


class GrocyAIBarcodeLookupStatusSensor(_StaticStatusSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="barcode_lookup_status",
            unique_suffix="barcode_lookup_status",
            icon="mdi:barcode-scan",
        )


class GrocyAILlavaScanStatusSensor(_StaticStatusSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            translation_key="llava_scan_status",
            unique_suffix="llava_scan_status",
            icon="mdi:image-search-outline",
        )
