import aiohttp
from urllib.parse import urlencode

DEFAULT_ADDON_API_URL = "http://local-grocy-ai-assistant:8000"
FALLBACK_ADDON_API_URLS = (
    DEFAULT_ADDON_API_URL,
    "http://grocy-ai-assistant:8000",
    "http://grocy_ai_assistant:8000",
)
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
        normalized_base_url = (base_url or "").strip().rstrip("/")
        self._base_url = normalized_base_url or DEFAULT_ADDON_API_URL
        self._headers = {"Authorization": f"Bearer {api_key}"}
        if integration_version:
            self._headers["X-HA-Integration-Version"] = integration_version

    def _candidate_base_urls(self) -> list[str]:
        if self._base_url:
            normalized_base_url = self._base_url.rstrip("/")
            if normalized_base_url not in FALLBACK_ADDON_API_URLS:
                return [normalized_base_url]

        candidates: list[str] = []
        for candidate in (self._base_url, *FALLBACK_ADDON_API_URLS):
            normalized_candidate = (candidate or "").rstrip("/")
            if normalized_candidate and normalized_candidate not in candidates:
                candidates.append(normalized_candidate)
        return candidates

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
        async with aiohttp.ClientSession(timeout=timeout) as session:
            request = session.get if method.upper() == "GET" else session.post
            request_kwargs = {"headers": self._headers}
            if method.upper() != "GET":
                request_kwargs["json"] = json_payload
            async with request(
                f"{self._base_url}{request_path}",
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
