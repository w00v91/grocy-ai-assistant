from grocy_ai_assistant.config.settings import Settings
from grocy_ai_assistant.services.grocy_client import GrocyClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_find_product_by_name_returns_exact_match(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse([
            {"id": 1, "name": "Mozzarella"},
            {"id": 2, "name": "Gouda"},
        ])

    monkeypatch.setattr("grocy_ai_assistant.services.grocy_client.requests.get", fake_get)

    client = GrocyClient(
        Settings(api_key="x", addon_version="a", required_integration_version="1", grocy_api_key="g")
    )

    assert client.find_product_by_name("mozzarella") == {"id": 1, "name": "Mozzarella"}


def test_find_product_by_name_returns_vector_match_for_typo(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse([
            {"id": 1, "name": "Mozzarella"},
            {"id": 2, "name": "Butter"},
        ])

    monkeypatch.setattr("grocy_ai_assistant.services.grocy_client.requests.get", fake_get)

    client = GrocyClient(
        Settings(api_key="x", addon_version="a", required_integration_version="1", grocy_api_key="g")
    )

    assert client.find_product_by_name("mozarella") == {"id": 1, "name": "Mozzarella"}


def test_find_product_by_name_returns_none_when_similarity_is_too_low(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse([
            {"id": 1, "name": "Mozzarella"},
            {"id": 2, "name": "Butter"},
        ])

    monkeypatch.setattr("grocy_ai_assistant.services.grocy_client.requests.get", fake_get)

    client = GrocyClient(
        Settings(api_key="x", addon_version="a", required_integration_version="1", grocy_api_key="g")
    )

    assert client.find_product_by_name("schraubenzieher") is None
