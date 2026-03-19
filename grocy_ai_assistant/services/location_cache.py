from __future__ import annotations

import logging
import threading

import requests

from grocy_ai_assistant.config.settings import Settings

logger = logging.getLogger(__name__)


class LocationCache:
    """Caches Grocy locations and refreshes them periodically in the background."""

    def __init__(
        self,
        settings: Settings,
        refresh_interval_seconds: int = 3600,
    ):
        self._settings = settings
        self._refresh_interval_seconds = max(refresh_interval_seconds, 60)
        self._stop_event = threading.Event()
        self._refresh_thread: threading.Thread | None = None
        self._refresh_lock = threading.Lock()
        self._locations: list[dict] = []

    def start(self) -> None:
        if self._refresh_thread and self._refresh_thread.is_alive():
            return

        self._stop_event.clear()
        if not self._settings.grocy_api_key:
            logger.info("Lager-Cache wird nicht gestartet: grocy_api_key fehlt")
            return

        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            name="grocy-location-cache-refresh",
            daemon=True,
        )
        self._refresh_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=2)

    def get_locations(self) -> list[dict]:
        with self._refresh_lock:
            if self._locations:
                return list(self._locations)

        self.refresh_locations()
        with self._refresh_lock:
            return list(self._locations)

    def refresh_locations(self) -> int:
        if not self._settings.grocy_api_key:
            logger.warning("Lager-Cache-Refresh übersprungen: grocy_api_key fehlt")
            return 0

        try:
            response = requests.get(
                f"{self._settings.grocy_base_url.rstrip('/')}/objects/locations",
                headers={"GROCY-API-KEY": self._settings.grocy_api_key},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            locations = payload if isinstance(payload, list) else []
        except requests.RequestException as error:
            logger.warning("Lager-Cache konnte Standorte nicht laden: %s", error)
            return 0

        normalized_locations = [
            {"id": int(item.get("id")), "name": str(item.get("name") or "")}
            for item in locations
            if item.get("id") is not None
        ]
        normalized_locations.sort(key=lambda item: item["name"].casefold())

        with self._refresh_lock:
            self._locations = normalized_locations

        logger.info("Lager-Cache aktualisiert: %s Standorte", len(normalized_locations))
        return len(normalized_locations)

    def _refresh_loop(self) -> None:
        self.refresh_locations()
        while not self._stop_event.wait(self._refresh_interval_seconds):
            self.refresh_locations()
