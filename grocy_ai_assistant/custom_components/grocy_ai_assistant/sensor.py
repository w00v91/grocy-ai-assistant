import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import (
    COORDINATOR_INVENTORY,
    COORDINATOR_RECIPE_SUGGESTIONS,
    COORDINATOR_STATUS,
    get_entry_coordinators,
)
from .entity import build_device_info
from .runtime import (
    RUNTIME_ANALYSIS_STATUS,
    RUNTIME_BARCODE_STATUS,
    RUNTIME_LLAVA_STATUS,
    RUNTIME_RESPONSE,
    RUNTIME_RESPONSE_TIME_AVG,
    RUNTIME_RESPONSE_TIME_LAST,
    async_runtime_signal,
    get_runtime_sensor_payload,
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
    def __init__(self, entry):
        self._entry = entry

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
        data_key: str,
        fallback_native_value,
    ):
        _BaseAddonSensor.__init__(self, entry)
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


class _RuntimeAddonSensor(_BaseAddonSensor):
    def __init__(
        self,
        entry,
        *,
        runtime_key: str,
        name: str,
        unique_suffix: str,
        fallback_native_value,
        icon: str,
        entity_category=EntityCategory.DIAGNOSTIC,
    ):
        super().__init__(entry)
        self._runtime_key = runtime_key
        self._fallback_native_value = fallback_native_value
        self._default_icon = icon
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_entity_category = entity_category

    def _payload(self) -> dict:
        if not hasattr(self, "hass"):
            return {}
        return get_runtime_sensor_payload(
            self.hass, self._entry.entry_id, self._runtime_key
        )

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                async_runtime_signal(self._entry.entry_id, self._runtime_key),
                self._handle_runtime_update,
            )
        )

    def _handle_runtime_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._payload().get("state", self._fallback_native_value)

    @property
    def icon(self):
        return self._payload().get("icon", self._default_icon)

    @property
    def extra_state_attributes(self):
        return dict(self._payload().get("attributes") or {})


class GrocyAISensor(_CoordinatorAddonSensor):
    """Sensor for add-on availability."""

    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            data_key="status",
            fallback_native_value="Offline",
        )
        self._attr_name = "Grocy AI Status"
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_icon = "mdi:robot"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class GrocyAIUpdateRequiredSensor(_CoordinatorAddonSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            data_key="update_required",
            fallback_native_value="Unbekannt",
        )
        self._attr_name = "Grocy AI Home Assistant Update erforderlich"
        self._attr_unique_id = f"{entry.entry_id}_ha_update_required"
        self._attr_icon = "mdi:update"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class GrocyAIResponseSensor(_RuntimeAddonSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            runtime_key=RUNTIME_RESPONSE,
            name="Grocy AI Response",
            unique_suffix="response_text",
            fallback_native_value="Bereit",
            icon="mdi:comment-text-outline",
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        _LOGGER.info("Response Sensor registriert und bereit.")


class GrocyAILastResponseTimeSensor(_RuntimeAddonSensor):
    """Diagnostic sensor containing the duration of the latest AI request."""

    def __init__(self, entry):
        super().__init__(
            entry,
            runtime_key=RUNTIME_RESPONSE_TIME_LAST,
            name="Grocy AI KI Antwortzeit (letzte Anfrage)",
            unique_suffix="ai_response_time_last_ms",
            fallback_native_value=None,
            icon="mdi:timer-outline",
        )
        self._attr_native_unit_of_measurement = "ms"
        self._attr_state_class = SensorStateClass.MEASUREMENT


class GrocyAIAverageResponseTimeSensor(_RuntimeAddonSensor):
    """Diagnostic sensor containing the average duration of AI requests."""

    def __init__(self, entry):
        super().__init__(
            entry,
            runtime_key=RUNTIME_RESPONSE_TIME_AVG,
            name="Grocy AI KI Antwortzeit (Durchschnitt)",
            unique_suffix="ai_response_time_avg_ms",
            fallback_native_value=None,
            icon="mdi:chart-line",
        )
        self._attr_native_unit_of_measurement = "ms"
        self._attr_state_class = SensorStateClass.MEASUREMENT


class GrocyAIShoppingListOpenCountSensor(_CoordinatorAddonSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            data_key="shopping_list_open_count",
            fallback_native_value=0,
        )
        self._attr_name = "Grocy AI Einkaufsliste offene Einträge"
        self._attr_unique_id = f"{entry.entry_id}_shopping_list_open_count"
        self._attr_icon = "mdi:cart-outline"


class GrocyAIStockProductCountSensor(_CoordinatorAddonSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            data_key="stock_products_total_count",
            fallback_native_value=0,
        )
        self._attr_name = "Grocy AI Lagerprodukte gesamt"
        self._attr_unique_id = f"{entry.entry_id}_stock_products_total_count"
        self._attr_icon = "mdi:fridge-outline"


class GrocyAIExpiringStockProductCountSensor(_CoordinatorAddonSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            data_key="stock_products_expiring_count",
            fallback_native_value=0,
        )
        self._attr_name = "Grocy AI Bald ablaufende Lagerprodukte"
        self._attr_unique_id = f"{entry.entry_id}_stock_products_expiring_count"
        self._attr_icon = "mdi:calendar-alert-outline"


class _RecipeSuggestionSensor(_CoordinatorAddonSensor):
    def __init__(
        self,
        entry,
        coordinator,
        *,
        name: str,
        suffix: str,
    ):
        super().__init__(
            entry,
            coordinator,
            data_key=suffix,
            fallback_native_value="Keine Vorschläge",
        )
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_icon = "mdi:chef-hat"


class GrocyAITopAIRecipeSuggestionSensor(_RecipeSuggestionSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            name="Grocy AI Top KI Rezeptvorschlag",
            suffix="recipe_suggestion_top_ai",
        )


class GrocyAITopGrocyRecipeSuggestionSensor(_RecipeSuggestionSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            name="Grocy AI Top Grocy Rezeptvorschlag",
            suffix="recipe_suggestion_top_grocy",
        )


class GrocyAISoonExpiringRecipeSuggestionSensor(_RecipeSuggestionSensor):
    def __init__(self, entry, coordinator):
        super().__init__(
            entry,
            coordinator,
            name="Grocy AI Rezeptvorschläge bald ablaufend",
            suffix="recipe_suggestion_expiring",
        )


class GrocyAIAnalysisStatusSensor(_RuntimeAddonSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            runtime_key=RUNTIME_ANALYSIS_STATUS,
            name="Grocy AI Analyse Status",
            unique_suffix="analysis_status",
            fallback_native_value="Bereit",
            icon="mdi:robot-outline",
        )


class GrocyAIBarcodeLookupStatusSensor(_RuntimeAddonSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            runtime_key=RUNTIME_BARCODE_STATUS,
            name="Grocy AI Barcode Scanner Status",
            unique_suffix="barcode_lookup_status",
            fallback_native_value="Bereit",
            icon="mdi:barcode-scan",
        )


class GrocyAILlavaScanStatusSensor(_RuntimeAddonSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            runtime_key=RUNTIME_LLAVA_STATUS,
            name="Grocy AI LLaVA Scanner Status",
            unique_suffix="llava_scan_status",
            fallback_native_value="Bereit",
            icon="mdi:image-search-outline",
        )
