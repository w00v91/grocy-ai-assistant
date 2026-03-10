import asyncio
import importlib.util
from pathlib import Path


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
    def __init__(self, timeout):
        self.timeout = timeout
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers):
        self.calls.append(("GET", url, headers, None))
        return FakeResponse(200, {"status": "Verbunden"})

    def post(self, url, json, headers):
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
    search_payload = asyncio.run(client.dashboard_search("Hafermilch"))

    assert status_payload == {"status": "Verbunden", "_http_status": 200}
    assert search_payload == {"success": True, "message": "ok", "_http_status": 200}

    request_headers = sessions[0].calls[0][2]
    assert request_headers["Authorization"] == "Bearer secret"
    assert request_headers["X-HA-Integration-Version"] == "1.2.3"

    method, url, _, body = sessions[1].calls[0]
    assert method == "POST"
    assert url == "http://localhost:8000/api/dashboard/search"
    assert body == {"name": "Hafermilch"}


def test_addon_client_uses_default_ingress_path(monkeypatch):
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
    assert url == "/api/hassio_ingress/grocy_ai_assistant/api/status"
