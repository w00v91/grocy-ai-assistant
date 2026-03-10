from grocy_ai_assistant.api import routes


def test_analyze_product_returns_detector_payload(client, monkeypatch):
    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def analyze_product_name(self, name):
            assert name == "Haferflocken"
            return {
                "name": "Haferflocken",
                "description": "Vollkorn",
                "location_id": 1,
                "qu_id_purchase": 2,
                "qu_id_stock": 2,
                "calories": 360,
            }

    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    response = client.post(
        "/api/analyze_product",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "Haferflocken"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["product_data"]["name"] == "Haferflocken"


def test_dashboard_search_reuses_existing_product(client, monkeypatch):
    calls = []

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_name(self, name):
            assert name == "Milch"
            return {"id": 7}

        def add_product_to_shopping_list(self, product_id, amount):
            calls.append((product_id, amount))

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "Milch"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "existing_added"
    assert calls == [(7, 1)]


def test_dashboard_search_creates_new_product_when_missing(client, monkeypatch):
    calls = {"created": None, "added": None}

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def analyze_product_name(self, name):
            return {
                "name": name,
                "description": "bio",
                "location_id": 1,
                "qu_id_purchase": 2,
                "qu_id_stock": 2,
                "calories": 100,
            }

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_name(self, name):
            return None

        def create_product(self, payload):
            calls["created"] = payload
            return 42

        def add_product_to_shopping_list(self, product_id, amount):
            calls["added"] = (product_id, amount)

    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": " Reis "},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "created_and_added"
    assert response.json()["product_id"] == 42
    assert calls["created"]["name"] == "Reis"
    assert calls["added"] == (42, 1)


def test_dashboard_search_rejects_blank_name(client):
    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "   "},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Bitte Produktname eingeben"}
