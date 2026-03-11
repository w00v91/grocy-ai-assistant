from grocy_ai_assistant.api import routes


def test_validation_errors_use_central_schema(client):
    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Ungültige Anfrageparameter"
    assert payload["error"]["path"] == "/api/dashboard/search"
    assert payload["error"]["details"]


def test_unexpected_errors_use_central_schema(client, monkeypatch):
    class ExplodingGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def search_products_by_partial_name(self, query):
            raise RuntimeError("kaputt")

    monkeypatch.setattr(routes, "GrocyClient", ExplodingGrocyClient)

    response = client.get(
        "/api/dashboard/search-variants?q=milch",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "internal_server_error"
    assert payload["error"]["message"] == "kaputt"
    assert payload["error"]["path"] == "/api/dashboard/search-variants"
