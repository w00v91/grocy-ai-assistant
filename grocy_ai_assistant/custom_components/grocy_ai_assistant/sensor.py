import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.entity import EntityCategory

from .addon_client import AddonClient
from .const import (
    CONF_DEBUG_MODE,
    DEFAULT_ADDON_BASE_URL,
    INTEGRATION_VERSION,
)
from .entity_payloads import (
    DEFAULT_EXPIRING_WITHIN_DAYS,
    build_expiring_stock_summary,
    build_recipe_summary,
    build_shopping_list_summary,
    build_stock_summary,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors for a config entry."""
    async_add_entities(
        [
            GrocyAISensor(entry),
            GrocyAIResponseSensor(entry),
            GrocyAIUpdateRequiredSensor(entry),
            GrocyAILastResponseTimeSensor(entry),
            GrocyAIAverageResponseTimeSensor(entry),
            GrocyAIShoppingListOpenCountSensor(entry),
            GrocyAIStockProductCountSensor(entry),
            GrocyAIExpiringStockProductCountSensor(entry),
            GrocyAITopRecipeSuggestionSensor(entry),
            GrocyAISoonExpiringRecipeSuggestionSensor(entry),
            GrocyAIAnalysisStatusSensor(entry),
            GrocyAIBarcodeLookupStatusSensor(entry),
            GrocyAILlavaScanStatusSensor(entry),
        ],
        update_before_add=True,
    )


class _BaseAddonSensor(SensorEntity):
    def __init__(self, entry):
        self._entry = entry

    def _build_client(self) -> AddonClient:
        conf = {**self._entry.data, **self._entry.options}
        return AddonClient(
            conf.get("addon_base_url", DEFAULT_ADDON_BASE_URL),
            conf.get("api_key", ""),
            integration_version=INTEGRATION_VERSION,
        )


class _PollingAddonSensor(_BaseAddonSensor):
    def __init__(self, entry):
        super().__init__(entry)
        self._debug_mode = bool(entry.options.get(CONF_DEBUG_MODE, False))

    async def async_update(self):
        try:
            await self._async_update_native_value()
        except Exception as error:
            self._attr_available = False
            if self._debug_mode:
                _LOGGER.debug("Sensorabfrage fehlgeschlagen (%s): %s", self.name, error)

    async def _async_update_native_value(self):
        raise NotImplementedError


class GrocyAISensor(_PollingAddonSensor):
    """Sensor for add-on availability."""

    def __init__(self, entry):
        super().__init__(entry)
        self._attr_name = "Grocy AI Status"
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_native_value = "Initialisiere..."
        self._attr_icon = "mdi:robot"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def _async_update_native_value(self):
        payload = await self._build_client().get_status()
        self._attr_available = True
        if payload.get("_http_status") == 200:
            self._attr_native_value = "Online"
            self._attr_extra_state_attributes = {
                "addon_version": payload.get("addon_version", "unbekannt"),
                "required_integration_version": payload.get(
                    "required_integration_version", "unbekannt"
                ),
                "homeassistant_restart_required": payload.get(
                    "homeassistant_restart_required", False
                ),
            }
        else:
            self._attr_native_value = f"Error {payload.get('_http_status')}"


class GrocyAIUpdateRequiredSensor(_PollingAddonSensor):
    def __init__(self, entry):
        super().__init__(entry)
        self._attr_name = "Grocy AI Home Assistant Update erforderlich"
        self._attr_unique_id = f"{entry.entry_id}_ha_update_required"
        self._attr_native_value = "Nein"
        self._attr_icon = "mdi:update"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def _async_update_native_value(self):
        payload = await self._build_client().get_status()
        self._attr_available = True
        if payload.get("_http_status") != 200:
            self._attr_native_value = "Unbekannt"
            return

        restart_required = bool(payload.get("homeassistant_restart_required", False))
        self._attr_native_value = "Ja" if restart_required else "Nein"
        self._attr_extra_state_attributes = {
            "required_integration_version": payload.get(
                "required_integration_version", "unbekannt"
            ),
            "current_integration_version": INTEGRATION_VERSION,
            "reason": payload.get("update_reason", ""),
        }


class _StaticStatusSensor(SensorEntity):
    def __init__(self, entry, *, name: str, unique_suffix: str, icon: str):
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_native_value = "Bereit"
        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def should_poll(self):
        return False


class GrocyAIResponseSensor(_StaticStatusSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            name="Grocy AI Response",
            unique_suffix="response_text",
            icon="mdi:comment-text-outline",
        )

    @property
    def device_info(self):
        return {
            "identifiers": {("domain", "grocy_ai_assistant")},
            "name": "Grocy AI Assistant",
            "manufacturer": "Eigene Integration",
        }

    async def async_added_to_hass(self):
        _LOGGER.info("Response Sensor registriert und bereit.")


class GrocyAILastResponseTimeSensor(SensorEntity):
    """Diagnostic sensor containing the duration of the latest AI request."""

    def __init__(self, entry):
        self._attr_name = "Grocy AI KI Antwortzeit (letzte Anfrage)"
        self._attr_unique_id = f"{entry.entry_id}_ai_response_time_last_ms"
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = "ms"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:timer-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class GrocyAIAverageResponseTimeSensor(SensorEntity):
    """Diagnostic sensor containing the average duration of AI requests."""

    def __init__(self, entry):
        self._attr_name = "Grocy AI KI Antwortzeit (Durchschnitt)"
        self._attr_unique_id = f"{entry.entry_id}_ai_response_time_avg_ms"
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = "ms"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:chart-line"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class GrocyAIShoppingListOpenCountSensor(_PollingAddonSensor):
    def __init__(self, entry):
        super().__init__(entry)
        self._attr_name = "Grocy AI Einkaufsliste offene Einträge"
        self._attr_unique_id = f"{entry.entry_id}_shopping_list_open_count"
        self._attr_native_value = 0
        self._attr_icon = "mdi:cart-outline"

    async def _async_update_native_value(self):
        payload = await self._build_client().get_shopping_list()
        self._attr_available = payload.get("_http_status") == 200
        if not self._attr_available:
            self._attr_native_value = None
            return

        count, attributes = build_shopping_list_summary(payload.get("items") or [])
        self._attr_native_value = count
        self._attr_extra_state_attributes = attributes


class GrocyAIStockProductCountSensor(_PollingAddonSensor):
    def __init__(self, entry):
        super().__init__(entry)
        self._attr_name = "Grocy AI Lagerprodukte gesamt"
        self._attr_unique_id = f"{entry.entry_id}_stock_products_total_count"
        self._attr_native_value = 0
        self._attr_icon = "mdi:fridge-outline"

    async def _async_update_native_value(self):
        payload = await self._build_client().get_stock_products()
        self._attr_available = payload.get("_http_status") == 200
        if not self._attr_available:
            self._attr_native_value = None
            return

        count, attributes = build_stock_summary(payload.get("items") or [])
        self._attr_native_value = count
        self._attr_extra_state_attributes = attributes


class GrocyAIExpiringStockProductCountSensor(_PollingAddonSensor):
    def __init__(self, entry):
        super().__init__(entry)
        self._attr_name = "Grocy AI Bald ablaufende Lagerprodukte"
        self._attr_unique_id = f"{entry.entry_id}_stock_products_expiring_count"
        self._attr_native_value = 0
        self._attr_icon = "mdi:calendar-alert-outline"

    async def _async_update_native_value(self):
        payload = await self._build_client().get_stock_products()
        self._attr_available = payload.get("_http_status") == 200
        if not self._attr_available:
            self._attr_native_value = None
            return

        count, attributes = build_expiring_stock_summary(
            payload.get("items") or [],
            expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
        )
        self._attr_native_value = count
        self._attr_extra_state_attributes = attributes


class _RecipeSuggestionSensor(_PollingAddonSensor):
    def __init__(self, entry, *, soon_expiring_only: bool, name: str, suffix: str):
        super().__init__(entry)
        self._soon_expiring_only = soon_expiring_only
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_native_value = "Keine Vorschläge"
        self._attr_icon = "mdi:chef-hat"

    async def _async_update_native_value(self):
        payload = await self._build_client().get_recipe_suggestions(
            soon_expiring_only=self._soon_expiring_only,
            expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
        )
        self._attr_available = payload.get("_http_status") == 200
        if not self._attr_available:
            self._attr_native_value = "Fehler"
            return

        state, attributes = build_recipe_summary(
            payload,
            soon_expiring_only=self._soon_expiring_only,
            expiring_within_days=DEFAULT_EXPIRING_WITHIN_DAYS,
        )
        self._attr_native_value = state
        self._attr_extra_state_attributes = attributes


class GrocyAITopRecipeSuggestionSensor(_RecipeSuggestionSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            soon_expiring_only=False,
            name="Grocy AI Top Rezeptvorschlag",
            suffix="recipe_suggestion_top",
        )


class GrocyAISoonExpiringRecipeSuggestionSensor(_RecipeSuggestionSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            soon_expiring_only=True,
            name="Grocy AI Rezeptvorschläge bald ablaufend",
            suffix="recipe_suggestion_expiring",
        )


class GrocyAIAnalysisStatusSensor(_StaticStatusSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            name="Grocy AI Analyse Status",
            unique_suffix="analysis_status",
            icon="mdi:robot-outline",
        )


class GrocyAIBarcodeLookupStatusSensor(_StaticStatusSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            name="Grocy AI Barcode Scanner Status",
            unique_suffix="barcode_lookup_status",
            icon="mdi:barcode-scan",
        )


class GrocyAILlavaScanStatusSensor(_StaticStatusSensor):
    def __init__(self, entry):
        super().__init__(
            entry,
            name="Grocy AI LLaVA Scanner Status",
            unique_suffix="llava_scan_status",
            icon="mdi:image-search-outline",
        )
