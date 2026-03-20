import asyncio
import importlib.util
from pathlib import Path

import aiohttp


module_path = (
    Path(__file__).resolve().parents[2]
    / "grocy_ai_assistant"
    / "custom_components"
    / "grocy_ai_assistant"
    / "addon_client.py"
)
spec = importlib.util.spec_from_file_location("addon_client_module", module_path)
addon_client_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(addon_client_module)
AddonClient = addon_client_module.AddonClient


class FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._payload


class FakeSession:
    def __init__(self, timeout, *, fail_urls=None):
        self.timeout = timeout
        self.calls = []
        self.fail_urls = set(fail_urls or [])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers):
        if url in self.fail_urls:
            raise aiohttp.ClientConnectionError(f"failed to connect to {url}")
        self.calls.append(("GET", url, headers, None))
        return FakeResponse(200, {"status": "Verbunden"})

    def post(self, url, json, headers):
        if url in self.fail_urls:
            raise aiohttp.ClientConnectionError(f"failed to connect to {url}")
        self.calls.append(("POST", url, headers, json))
        return FakeResponse(200, {"success": True, "message": "ok"})


def test_addon_client_sends_homeassistant_version_header(monkeypatch):
    sessions = []

    def fake_client_session(*, timeout):
        session = FakeSession(timeout)
        sessions.append(session)
        return session

    monkeypatch.setattr(
        addon_client_module.aiohttp, "ClientSession", fake_client_session
    )

    client = AddonClient(
        base_url="http://localhost:8000/",
        api_key="secret",
        integration_version="1.2.3",
    )

    status_payload = asyncio.run(client.get_status())
    search_payload = asyncio.run(client.sync_product("Hafermilch"))

    assert status_payload == {"status": "Verbunden", "_http_status": 200}
    assert search_payload == {"success": True, "message": "ok", "_http_status": 200}

    request_headers = sessions[0].calls[0][2]
    assert request_headers["Authorization"] == "Bearer secret"
    assert request_headers["X-HA-Integration-Version"] == "1.2.3"
    assert (
        sessions[0].calls[0][1] == "http://local-grocy-ai-assistant:8000/api/v1/status"
    )

    method, url, _, body = sessions[1].calls[0]
    assert method == "POST"
    assert url == "http://local-grocy-ai-assistant:8000/api/v1/grocy/sync"
    assert body == {"name": "Hafermilch"}


def test_addon_client_uses_default_internal_api_url(monkeypatch):
    sessions = []

    def fake_client_session(*, timeout):
        session = FakeSession(timeout)
        sessions.append(session)
        return session

    monkeypatch.setattr(
        addon_client_module.aiohttp, "ClientSession", fake_client_session
    )

    client = AddonClient(base_url="", api_key="secret")
    asyncio.run(client.get_status())

    method, url, _, _ = sessions[0].calls[0]
    assert method == "GET"
    assert url == "http://local-grocy-ai-assistant:8000/api/v1/status"


def test_addon_client_ignores_loopback_base_url(monkeypatch):
    sessions = []

    def fake_client_session(*, timeout):
        session = FakeSession(timeout)
        sessions.append(session)
        return session

    monkeypatch.setattr(
        addon_client_module.aiohttp, "ClientSession", fake_client_session
    )

    client = AddonClient(base_url="http://localhost:8000", api_key="secret")
    asyncio.run(client.get_status())

    method, url, _, _ = sessions[0].calls[0]
    assert method == "GET"
    assert url == "http://local-grocy-ai-assistant:8000/api/v1/status"


def test_addon_client_falls_back_to_secondary_internal_host(monkeypatch):
    sessions = []

    def fake_client_session(*, timeout):
        session = FakeSession(
            timeout,
            fail_urls={"http://local-grocy-ai-assistant:8000/api/v1/status"},
        )
        sessions.append(session)
        return session

    monkeypatch.setattr(
        addon_client_module.aiohttp, "ClientSession", fake_client_session
    )

    client = AddonClient(base_url="", api_key="secret")
    payload = asyncio.run(client.get_status())

    assert payload == {"status": "Verbunden", "_http_status": 200}
    assert sessions[0].calls[0][1] == "http://grocy-ai-assistant:8000/api/v1/status"


def test_addon_client_uses_v1_machine_endpoints_for_read_operations(monkeypatch):
    sessions = []

    def fake_client_session(*, timeout):
        session = FakeSession(timeout)
        sessions.append(session)
        return session

    monkeypatch.setattr(
        addon_client_module.aiohttp, "ClientSession", fake_client_session
    )

    client = AddonClient(base_url="http://localhost:8000", api_key="secret")

    asyncio.run(client.get_shopping_list())
    asyncio.run(client.get_stock_products())
    asyncio.run(
        client.get_recipe_suggestions(
            soon_expiring_only=True,
            expiring_within_days=5,
        )
    )
    asyncio.run(client.lookup_barcode("4008400408400"))

    assert (
        sessions[0].calls[0][1]
        == "http://local-grocy-ai-assistant:8000/api/v1/shopping-list"
    )
    assert (
        sessions[1].calls[0][1] == "http://local-grocy-ai-assistant:8000/api/v1/stock"
    )
    assert (
        sessions[2].calls[0][1]
        == "http://local-grocy-ai-assistant:8000/api/v1/recipes?soon_expiring_only=True&expiring_within_days=5"
    )
    assert (
        sessions[3].calls[0][1]
        == "http://local-grocy-ai-assistant:8000/api/v1/barcode/4008400408400"
    )
