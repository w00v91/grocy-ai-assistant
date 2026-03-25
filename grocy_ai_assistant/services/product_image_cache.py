from __future__ import annotations

import binascii
import hashlib
import logging
import threading
from base64 import b64decode
from pathlib import Path
from urllib.parse import urlparse

import requests

from grocy_ai_assistant.config.settings import Settings
from grocy_ai_assistant.core.picture_urls import build_product_picture_url

logger = logging.getLogger(__name__)


class ProductImageCache:
    """Mirrors Grocy product images locally and refreshes them periodically."""

    def __init__(
        self,
        settings: Settings,
        cache_dir: str = "/tmp/grocy-product-image-cache",
        refresh_interval_seconds: int = 3600,
    ):
        self._settings = settings
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._refresh_interval_seconds = max(refresh_interval_seconds, 60)
        self._stop_event = threading.Event()
        self._initial_refresh_done = threading.Event()
        self._refresh_thread: threading.Thread | None = None
        self._refresh_lock = threading.Lock()
        self._last_refresh_count: int | None = None
        self._last_refresh_status: str = "not_started"
        self._last_refresh_error: str = ""

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def start(self) -> None:
        if self._refresh_thread and self._refresh_thread.is_alive():
            return

        self._stop_event.clear()
        self._initial_refresh_done.clear()
        if not self._settings.grocy_api_key:
            logger.info("Produktbild-Cache wird nicht gestartet: grocy_api_key fehlt")
            self._last_refresh_count = 0
            self._last_refresh_status = "skipped_missing_api_key"
            self._last_refresh_error = ""
            self._initial_refresh_done.set()
            return

        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            name="grocy-product-image-cache-refresh",
            daemon=True,
        )
        self._refresh_thread.start()

    def wait_for_initial_refresh(self, timeout: float | None = None) -> bool:
        return self._initial_refresh_done.wait(timeout)

    def get_last_refresh_status(self) -> dict[str, int | str | None]:
        return {
            "status": self._last_refresh_status,
            "refreshed_images": self._last_refresh_count,
            "error": self._last_refresh_error,
        }

    def stop(self) -> None:
        self._stop_event.set()
        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=2)

    def refresh_all_product_images(self) -> int:
        if not self._settings.grocy_api_key:
            logger.warning("Bildcache-Refresh übersprungen: grocy_api_key fehlt")
            self._last_refresh_count = 0
            self._last_refresh_status = "skipped_missing_api_key"
            self._last_refresh_error = ""
            return 0

        with self._refresh_lock:
            try:
                products = self._fetch_products()
            except requests.RequestException as error:
                logger.warning(
                    "Produktbild-Cache konnte Produktliste nicht laden: %s", error
                )
                self._last_refresh_count = 0
                self._last_refresh_status = "failed_product_fetch"
                self._last_refresh_error = str(error)
                return 0
            refreshed_images = 0
            for product in products:
                source_urls = self._build_product_picture_urls(product)
                if not source_urls:
                    continue

                for source_url in source_urls:
                    if self._download_to_cache(source_url):
                        refreshed_images += 1
                        break

            logger.info("Produktbild-Cache aktualisiert: %s Bilder", refreshed_images)
            self._last_refresh_count = refreshed_images
            self._last_refresh_status = "ok"
            self._last_refresh_error = ""
            return refreshed_images

    def get_cached_image(self, src: str) -> tuple[bytes | None, str]:
        source_url = self._build_product_picture_url(src)
        if not source_url:
            return None, ""

        cache_path = self._cache_path_for_url(source_url)
        if not cache_path.exists():
            if not self._download_to_cache(source_url):
                return None, ""

        try:
            content = cache_path.read_bytes()
            media_type = self._guess_media_type(cache_path.suffix)
            return content, media_type
        except OSError as error:
            logger.error(
                "Konnte Bildcache-Datei nicht lesen (%s): %s", cache_path, error
            )
            return None, ""

    def _refresh_loop(self) -> None:
        try:
            self.refresh_all_product_images()
        finally:
            self._initial_refresh_done.set()
        while not self._stop_event.wait(self._refresh_interval_seconds):
            self.refresh_all_product_images()

    def _fetch_products(self) -> list[dict]:
        response = requests.get(
            f"{self._settings.grocy_base_url.rstrip('/')}/objects/products",
            headers={"GROCY-API-KEY": self._settings.grocy_api_key},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def _build_product_picture_urls(self, product: dict) -> list[str]:
        candidate_values: list[str] = []
        for key in ("picture_url", "picture_file_name"):
            raw_value = (product.get(key) or "").strip()
            if raw_value and raw_value not in candidate_values:
                candidate_values.append(raw_value)

        source_urls: list[str] = []
        for value in candidate_values:
            source_url = self._build_product_picture_url(value)
            if source_url and source_url not in source_urls:
                source_urls.append(source_url)
        return source_urls

    def _build_product_picture_url(self, picture_value: str) -> str:
        value = (picture_value or "").strip()
        if not value or value.startswith("data:"):
            return ""

        return build_product_picture_url(value, self._settings)

    def _download_to_cache(self, source_url: str) -> bool:
        parsed_source = urlparse(source_url)
        parsed_grocy = urlparse(self._settings.grocy_base_url)
        if (
            parsed_source.scheme not in {"http", "https"}
            or parsed_source.netloc != parsed_grocy.netloc
        ):
            logger.warning(
                "Überspringe externes Produktbild außerhalb des Grocy-Hosts: %s",
                source_url,
            )
            return False

        candidate_urls = [source_url]
        if parsed_source.path.startswith("/api/files/"):
            candidate_urls.append(
                parsed_source._replace(
                    path=parsed_source.path.removeprefix("/api")
                ).geturl()
            )
        elif parsed_source.path.startswith("/files/"):
            candidate_urls.append(
                parsed_source._replace(path=f"/api{parsed_source.path}").geturl()
            )

        for candidate_url in candidate_urls:
            cache_path = self._cache_path_for_url(source_url)
            try:
                response = requests.get(
                    candidate_url,
                    headers={"GROCY-API-KEY": self._settings.grocy_api_key},
                    timeout=30,
                )
                response.raise_for_status()
                cache_path.write_bytes(response.content)
                return True
            except requests.HTTPError as error:
                is_not_found = (
                    error.response is not None and error.response.status_code == 404
                )
                has_fallback = candidate_url != candidate_urls[-1]
                if is_not_found and has_fallback:
                    logger.info(
                        "Produktbild unter %s nicht gefunden, versuche Fallback-URL %s",
                        candidate_url,
                        candidate_urls[-1],
                    )
                    continue
                logger.warning(
                    "Produktbild konnte nicht gecacht werden (%s): %s",
                    candidate_url,
                    error,
                )
                return False
            except (requests.RequestException, OSError) as error:
                logger.warning(
                    "Produktbild konnte nicht gecacht werden (%s): %s",
                    candidate_url,
                    error,
                )
                return False

        return False

    def _cache_path_for_url(self, source_url: str) -> Path:
        parsed = urlparse(source_url)
        extension = Path(parsed.path).suffix
        if not extension:
            encoded_name = Path(parsed.path).name
            try:
                decoded_name = b64decode(encoded_name).decode("utf-8")
                extension = Path(decoded_name).suffix
            except (binascii.Error, UnicodeDecodeError):
                extension = ""

        extension = extension or ".img"
        file_name = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{file_name}{extension[:10]}"

    @staticmethod
    def _guess_media_type(extension: str) -> str:
        normalized = extension.lower()
        if normalized == ".png":
            return "image/png"
        if normalized in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if normalized == ".webp":
            return "image/webp"
        if normalized == ".gif":
            return "image/gif"
        return "application/octet-stream"
