from .const import DEFAULT_ADDON_INGRESS_PATH

import aiohttp


class AddonClient:
    """HTTP helper for communication with the Grocy AI add-on API."""

    def __init__(
        self, base_url: str, api_key: str, integration_version: str | None = None
    ):
        self._base_url = (base_url or DEFAULT_ADDON_INGRESS_PATH).rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        if integration_version:
            self._headers["X-HA-Integration-Version"] = integration_version

    async def get_status(self) -> dict:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{self._base_url}/api/status", headers=self._headers
            ) as response:
                payload = await response.json()
                payload["_http_status"] = response.status
                return payload

    async def dashboard_search(self, product_name: str) -> dict:
        timeout = aiohttp.ClientTimeout(total=180)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self._base_url}/api/dashboard/search",
                json={"name": product_name},
                headers=self._headers,
            ) as response:
                payload = await response.json()
                payload["_http_status"] = response.status
                return payload
