import asyncio
from ipaddress import ip_address
import os
from typing import Mapping
from urllib.parse import urlencode
from urllib.parse import urlparse

import aiohttp

ADDON_SLUG = "grocy_ai_assistant"
DEFAULT_ADDON_API_URL = "http://local-grocy-ai-assistant:8000"
FALLBACK_ADDON_API_URLS = (
    DEFAULT_ADDON_API_URL,
    "http://grocy-ai-assistant:8000",
    "http://grocy_ai_assistant:8000",
)
DEFAULT_SUPERVISOR_URL = "http://supervisor"
_ADDON_URL_HINT = (
    "Setze in der Integration die API-Basis-URL auf den Home-Assistant-App-Hostnamen "
    "im Format http://{repo}-{slug}:8000 (Unterstriche durch Bindestriche ersetzen), "
    "z. B. http://local-grocy-ai-assistant:8000."
)


class AddonClient:
    """HTTP helper for communication with the Grocy AI add-on API."""

    def __init__(
        self, base_url: str, api_key: str, integration_version: str | None = None
    ):
        normalized_base_url = self._normalize_base_url(base_url)
        self._base_url = normalized_base_url or DEFAULT_ADDON_API_URL
        self._headers = {"Authorization": f"Bearer {api_key}"}
        if integration_version:
            self._headers["X-HA-Integration-Version"] = integration_version

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str:
        normalized_base_url = (base_url or "").strip().rstrip("/")
        if not normalized_base_url:
            return DEFAULT_ADDON_API_URL
        if AddonClient._is_loopback_url(normalized_base_url):
            return DEFAULT_ADDON_API_URL
        return normalized_base_url

    @staticmethod
    def _is_loopback_url(url: str) -> bool:
        parsed_url = urlparse(url)
        hostname = (parsed_url.hostname or "").strip()
        if not hostname:
            return False
        if hostname.lower() == "localhost":
            return True
        try:
            return ip_address(hostname).is_loopback
        except ValueError:
            return False

    @staticmethod
    def _deduplicated_urls(*candidate_groups: list[str] | tuple[str, ...]) -> list[str]:
        candidates: list[str] = []
        for group in candidate_groups:
            for candidate in group:
                normalized_candidate = (candidate or "").rstrip("/")
                if normalized_candidate and normalized_candidate not in candidates:
                    candidates.append(normalized_candidate)
        return candidates

    async def _candidate_base_urls(self, session: aiohttp.ClientSession) -> list[str]:
        supervisor_candidates = await self._supervisor_base_urls(session)
        if self._base_url in FALLBACK_ADDON_API_URLS:
            return self._deduplicated_urls(
                supervisor_candidates,
                [self._base_url],
                FALLBACK_ADDON_API_URLS,
            )
        return self._deduplicated_urls(
            [self._base_url],
            supervisor_candidates,
            FALLBACK_ADDON_API_URLS,
        )

    async def _supervisor_base_urls(self, session: aiohttp.ClientSession) -> list[str]:
        token = (os.getenv("SUPERVISOR_TOKEN") or "").strip()
        if not token:
            return []

        supervisor_url = (os.getenv("SUPERVISOR_URL") or DEFAULT_SUPERVISOR_URL).strip()
        if not supervisor_url:
            return []
        supervisor_url = supervisor_url.rstrip("/")
        if "://" not in supervisor_url:
            supervisor_url = f"http://{supervisor_url}"

        headers = {"Authorization": f"Bearer {token}"}
        addon_slug = await self._discover_addon_slug(session, supervisor_url, headers)
        if not addon_slug:
            return []

        payload = await self._supervisor_json(
            session,
            f"{supervisor_url}/addons/{addon_slug}/info",
            headers,
        )
        if not isinstance(payload, dict):
            return []

        port = int(payload.get("ingress_port") or 8000)
        candidates: list[str] = []
        hostname = str(payload.get("hostname") or "").strip()
        ip_address_value = str(payload.get("ip_address") or "").strip()
        if hostname:
            candidates.append(f"http://{hostname}:{port}")
        if ip_address_value:
            candidates.append(f"http://{ip_address_value}:{port}")
        return candidates

    async def _discover_addon_slug(
        self,
        session: aiohttp.ClientSession,
        supervisor_url: str,
        headers: dict[str, str],
    ) -> str | None:
        payload = await self._supervisor_json(
            session,
            f"{supervisor_url}/addons",
            headers,
        )
        addons = payload.get("addons") if isinstance(payload, dict) else None
        if not isinstance(addons, list):
            return None

        for addon in addons:
            if not isinstance(addon, dict):
                continue
            slug = str(addon.get("slug") or "").strip()
            if slug == ADDON_SLUG or slug.endswith(f"_{ADDON_SLUG}"):
                return slug
        return None

    async def _supervisor_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: dict[str, str],
    ) -> dict | list | None:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return None

        if isinstance(payload, dict) and isinstance(payload.get("data"), (dict, list)):
            return payload["data"]
        return payload if isinstance(payload, (dict, list)) else None

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict | None = None,
        query_params: dict | None = None,
        timeout_seconds: int = 30,
    ) -> dict | list:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        request_path = path
        if query_params:
            filtered_query = {
                key: value
                for key, value in query_params.items()
                if value not in (None, "")
            }
            if filtered_query:
                request_path = f"{path}?{urlencode(filtered_query)}"
        last_error: Exception | None = None
        async with aiohttp.ClientSession(timeout=timeout) as session:
            request = session.get if method.upper() == "GET" else session.post
            request_kwargs = {"headers": self._headers}
            if method.upper() != "GET":
                request_kwargs["json"] = json_payload

            candidate_base_urls = await self._candidate_base_urls(session)
            for candidate_base_url in candidate_base_urls:
                try:
                    async with request(
                        f"{candidate_base_url}{request_path}",
                        **request_kwargs,
                    ) as response:
                        payload = await response.json()
                        if isinstance(payload, dict):
                            payload["_http_status"] = response.status
                            return payload
                        return {
                            "items": payload,
                            "_http_status": response.status,
                        }
                except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                    last_error = error
                    continue

        if last_error is not None:
            raise last_error
        raise RuntimeError("Die Add-on-API konnte nicht erreicht werden")

    async def request_raw(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        query_params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: int = 30,
    ) -> dict:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        request_path = path
        if query_params:
            filtered_query = {
                key: value
                for key, value in query_params.items()
                if value not in (None, "")
            }
            if filtered_query:
                request_path = f"{path}?{urlencode(filtered_query)}"

        last_error: Exception | None = None
        async with aiohttp.ClientSession(timeout=timeout) as session:
            candidate_base_urls = await self._candidate_base_urls(session)
            for candidate_base_url in candidate_base_urls:
                try:
                    async with session.request(
                        method.upper(),
                        f"{candidate_base_url}{request_path}",
                        headers={**self._headers, **dict(headers or {})},
                        data=body,
                    ) as response:
                        return {
                            "status": response.status,
                            "body": await response.read(),
                            "headers": {
                                key: value
                                for key, value in response.headers.items()
                                if key.lower() in {"content-type", "cache-control"}
                            },
                        }
                except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                    last_error = error
                    continue

        if last_error is not None:
            raise last_error
        raise RuntimeError("Die Add-on-API konnte nicht erreicht werden")

    async def get_status(self) -> dict:
        return await self._request_json("GET", "/api/v1/status", timeout_seconds=10)

    async def get_health(self) -> dict:
        return await self._request_json("GET", "/api/v1/health", timeout_seconds=10)

    async def get_capabilities(self) -> dict:
        return await self._request_json(
            "GET", "/api/v1/capabilities", timeout_seconds=10
        )

    async def sync_product(self, product_name: str) -> dict:
        return await self._request_json(
            "POST",
            "/api/v1/grocy/sync",
            json_payload={"name": product_name},
            timeout_seconds=180,
        )

    async def dashboard_search(self, product_name: str) -> dict:
        return await self.sync_product(product_name)

    async def get_shopping_list(self) -> dict:
        return await self._request_json(
            "GET", "/api/v1/shopping-list", timeout_seconds=30
        )

    async def get_stock_products(self) -> dict:
        return await self._request_json("GET", "/api/v1/stock", timeout_seconds=30)

    async def get_recipe_suggestions(
        self,
        *,
        soon_expiring_only: bool = False,
        expiring_within_days: int = 3,
    ) -> dict:
        payload = {
            "soon_expiring_only": bool(soon_expiring_only),
            "expiring_within_days": max(1, int(expiring_within_days)),
        }
        return await self._request_json(
            "GET",
            "/api/v1/recipes",
            query_params=payload,
            timeout_seconds=60,
        )

    async def lookup_barcode(self, barcode: str) -> dict:
        normalized_barcode = str(barcode or "").strip()
        return await self._request_json(
            "GET",
            f"/api/v1/barcode/{normalized_barcode}",
            timeout_seconds=30,
        )

    async def scan_image(self, image_base64: str) -> dict:
        return await self._request_json(
            "POST",
            "/api/v1/scan/image",
            json_payload={"image_base64": image_base64},
            timeout_seconds=180,
        )

    async def scan_image_with_llava(self, image_base64: str) -> dict:
        return await self.scan_image(image_base64)

    async def rebuild_catalog(self) -> dict:
        return await self._request_json(
            "POST",
            "/api/v1/catalog/rebuild",
            json_payload={},
            timeout_seconds=180,
        )

    async def test_notifications(self) -> dict:
        return await self._request_json(
            "POST",
            "/api/v1/notifications/test",
            json_payload={},
            timeout_seconds=30,
        )
