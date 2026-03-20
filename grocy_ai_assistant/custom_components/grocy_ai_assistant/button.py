import logging

from homeassistant.components.button import ButtonEntity

from .addon_client import AddonClient
from .const import CONF_API_BASE_URL, DEFAULT_ADDON_BASE_URL, INTEGRATION_VERSION
from .entity import build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            GrocyAICatalogRebuildButton(entry),
            GrocyAINotificationTestButton(entry),
        ]
    )


class _BaseAddonButton(ButtonEntity):
    def __init__(self, entry, *, name: str, unique_suffix: str, icon: str):
        self._entry = entry
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_icon = icon

    def _build_client(self) -> AddonClient:
        conf = {**self._entry.data, **self._entry.options}
        return AddonClient(
            conf.get(
                CONF_API_BASE_URL,
                conf.get("addon_base_url", DEFAULT_ADDON_BASE_URL),
            ),
            conf.get("api_key", ""),
            integration_version=INTEGRATION_VERSION,
        )

    @property
    def device_info(self):
        return build_device_info(self._entry.entry_id)


class GrocyAICatalogRebuildButton(_BaseAddonButton):
    def __init__(self, entry):
        super().__init__(
            entry,
            name="Grocy AI Katalog neu aufbauen",
            unique_suffix="catalog_rebuild",
            icon="mdi:database-refresh-outline",
        )

    async def async_press(self) -> None:
        payload = await self._build_client().rebuild_catalog()
        if payload.get("_http_status") != 200:
            raise RuntimeError(payload.get("detail") or "Katalog-Neuaufbau fehlgeschlagen")
        _LOGGER.info("Grocy AI Katalog-Neuaufbau erfolgreich ausgelöst")


class GrocyAINotificationTestButton(_BaseAddonButton):
    def __init__(self, entry):
        super().__init__(
            entry,
            name="Grocy AI Test-Benachrichtigung",
            unique_suffix="notification_test",
            icon="mdi:bell-ring-outline",
        )

    async def async_press(self) -> None:
        payload = await self._build_client().test_notifications()
        if payload.get("_http_status") != 200:
            raise RuntimeError(
                payload.get("detail") or "Test-Benachrichtigung fehlgeschlagen"
            )
        _LOGGER.info("Grocy AI Test-Benachrichtigung erfolgreich ausgelöst")
