from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path
from urllib.parse import ParseResult, urljoin, urlparse

import requests

from grocy_ai_assistant.config.settings import Settings

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
        self._refresh_thread: threading.Thread | None = None
        self._refresh_lock = threading.Lock()

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def start(self) -> None:
        if self._refresh_thread and self._refresh_thread.is_alive():
            return

        self._stop_event.clear()
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            name="grocy-product-image-cache-refresh",
            daemon=True,
        )
        self._refresh_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=2)

    def refresh_all_product_images(self) -> int:
        if not self._settings.grocy_api_key:
            logger.warning("Bildcache-Refresh übersprungen: grocy_api_key fehlt")
            return 0

        with self._refresh_lock:
            try:
                products = self._fetch_products()
            except requests.RequestException as error:
                logger.warning("Produktbild-Cache konnte Produktliste nicht laden: %s", error)
                return 0
            refreshed_images = 0
            for product in products:
                picture_value = (product.get("picture_url") or product.get("picture_file_name") or "").strip()
                if not picture_value:
                    continue

                source_url = self._build_product_picture_url(picture_value)
                if not source_url:
                    continue

                if self._download_to_cache(source_url):
                    refreshed_images += 1

            logger.info("Produktbild-Cache aktualisiert: %s Bilder", refreshed_images)
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
            logger.error("Konnte Bildcache-Datei nicht lesen (%s): %s", cache_path, error)
            return None, ""

    def _refresh_loop(self) -> None:
        self.refresh_all_product_images()
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

    def _build_product_picture_url(self, picture_value: str) -> str:
        value = (picture_value or "").strip()
        if not value or value.startswith("data:"):
            return ""

        parsed_grocy_base = urlparse(self._settings.grocy_base_url.rstrip("/"))
        grocy_base_url = parsed_grocy_base.geturl().rstrip("/")

        if value.startswith(("http://", "https://")):
            parsed_picture = urlparse(value)
            if parsed_picture.hostname in {"localhost", "127.0.0.1", "::1", "homeassistant"}:
                return ParseResult(
                    scheme=parsed_grocy_base.scheme or parsed_picture.scheme,
                    netloc=parsed_grocy_base.netloc or parsed_picture.netloc,
                    path=parsed_picture.path,
                    params=parsed_picture.params,
                    query=parsed_picture.query,
                    fragment=parsed_picture.fragment,
                ).geturl()
            return value

        if "/" not in value:
            value = f"files/productpictures/{value}"

        if value.startswith("/"):
            return urljoin(f"{grocy_base_url}/", value)

        return f"{grocy_base_url}/{value.lstrip('/')}"

    def _download_to_cache(self, source_url: str) -> bool:
        parsed_source = urlparse(source_url)
        parsed_grocy = urlparse(self._settings.grocy_base_url)
        if parsed_source.scheme not in {"http", "https"} or parsed_source.netloc != parsed_grocy.netloc:
            logger.warning("Überspringe externes Produktbild außerhalb des Grocy-Hosts: %s", source_url)
            return False

        candidate_urls = [source_url]
        if parsed_source.path.startswith("/api/files/"):
            candidate_urls.append(
                parsed_source._replace(path=parsed_source.path.removeprefix("/api")).geturl()
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
                logger.warning("Produktbild konnte nicht gecacht werden (%s): %s", candidate_url, error)
                return False
            except (requests.RequestException, OSError) as error:
                logger.warning("Produktbild konnte nicht gecacht werden (%s): %s", candidate_url, error)
                return False

        return False

    def _cache_path_for_url(self, source_url: str) -> Path:
        parsed = urlparse(source_url)
        extension = Path(parsed.path).suffix or ".img"
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
