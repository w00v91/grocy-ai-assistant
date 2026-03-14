from grocy_ai_assistant.api import routes


def test_analyze_product_returns_detector_payload(client, monkeypatch):
    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def analyze_product_name(self, name, locations=None):
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

        def add_product_to_shopping_list(self, product_id, amount, best_before_date=""):
            calls.append((product_id, amount, best_before_date))

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "Milch"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "existing_added"
    assert calls == [(7, 1, "")]


def test_dashboard_search_uses_amount_prefix_from_name(client, monkeypatch):
    calls = []

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_name(self, name):
            assert name == "nudeln"
            return {"id": 7}

        def add_product_to_shopping_list(self, product_id, amount, best_before_date=""):
            calls.append((product_id, amount, best_before_date))

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "2 nudeln", "amount": 1},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "existing_added"
    assert calls == [(7, 2, "")]


def test_dashboard_search_creates_new_product_when_missing(client, monkeypatch):
    calls = {"created": None, "added": None}

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def analyze_product_name(self, name, locations=None):
            return {
                "name": name,
                "description": "bio",
                "location_id": 1,
                "qu_id_purchase": 2,
                "qu_id_stock": 2,
                "calories": 100,
            }

        def suggest_similar_products(self, name):
            return []

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_name(self, name):
            return None

        def search_products_by_partial_name(self, query):
            return []

        def create_product(self, payload):
            calls["created"] = payload
            return 42

        def add_product_to_shopping_list(self, product_id, amount, best_before_date=""):
            calls["added"] = (product_id, amount, best_before_date)

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
    assert calls["added"] == (42, 1, "")


def test_dashboard_search_rejects_blank_name(client):
    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "   "},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["message"] == "Bitte Produktname eingeben"
    assert payload["error"]["code"] == "bad_request"


def test_dashboard_search_variants_returns_partial_matches(client, monkeypatch):
    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def search_products_by_partial_name(self, query):
            assert query == "apf"
            return [
                {
                    "id": 1,
                    "name": "Apfel",
                    "picture_url": "files/productpictures/apfel.jpg",
                },
                {
                    "id": 2,
                    "name": "Apfelessig",
                    "picture_url": "files/productpictures/apfelessig.jpg",
                },
            ]

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/dashboard/search-variants?q=apf",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Apfel", "Apfelessig"]


def test_dashboard_search_variants_ignores_amount_prefix(client, monkeypatch):
    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def search_products_by_partial_name(self, query):
            assert query == "apf"
            return [
                {
                    "id": 1,
                    "name": "Apfel",
                    "picture_url": "files/productpictures/apfel.jpg",
                }
            ]

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/dashboard/search-variants?q=2%20apf",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Apfel"]


def test_dashboard_add_existing_product_adds_to_shopping_list(client, monkeypatch):
    calls = []

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def add_product_to_shopping_list(self, product_id, amount, best_before_date=""):
            calls.append((product_id, amount, best_before_date))

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/add-existing-product",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "product_id": 11,
            "product_name": "Apfel",
            "amount": 2.5,
            "best_before_date": "2026-12-31",
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "existing_added"
    assert calls == [(11, 2.5, "2026-12-31")]


def test_dashboard_search_returns_fallback_variants_for_incomplete_query(
    client, monkeypatch
):
    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def suggest_similar_products(self, name):
            assert name == "apf"
            return [{"name": "Apfel"}, {"name": "Apfelessig"}]

        def analyze_product_name(self, name, locations=None):
            raise AssertionError(
                "analyze_product_name should not run when fallback variants exist"
            )

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_name(self, name):
            return None

        def search_products_by_partial_name(self, query):
            if query == "apf":
                return [{"id": 1, "name": "Apfel", "picture_url": ""}]
            if query == "Apfelessig":
                return [{"id": 2, "name": "Apfelessig", "picture_url": ""}]
            return []

    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "apf"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["action"] == "variant_selection_required"
    assert [item["name"] for item in payload["variants"]] == ["Apfel", "Apfelessig"]


def test_dashboard_search_keeps_ai_variant_without_grocy_match(client, monkeypatch):
    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def suggest_similar_products(self, name):
            return [{"name": "Apfelschale"}]

        def analyze_product_name(self, name, locations=None):
            raise AssertionError(
                "analyze_product_name should not run when AI variant exists"
            )

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_name(self, name):
            return None

        def search_products_by_partial_name(self, query):
            return []

    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "apf"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "variant_selection_required"
    assert payload["variants"] == [
        {"id": None, "name": "Apfelschale", "picture_url": "", "source": "ai"}
    ]


def test_dashboard_search_generates_and_attaches_image_for_new_product(
    client, test_settings, monkeypatch
):
    test_settings.image_generation_enabled = True
    test_settings.openai_api_key = "sk-test"

    calls = {"attached": None}

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def analyze_product_name(self, name, locations=None):
            return {
                "name": name,
                "description": "bio",
                "location_id": 1,
                "qu_id_purchase": 2,
                "qu_id_stock": 2,
                "calories": 100,
            }

        def suggest_similar_products(self, name):
            return []

        def generate_product_image(self, name):
            return "/tmp/generated/apfel.png"

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_name(self, name):
            return None

        def search_products_by_partial_name(self, query):
            return []

        def create_product(self, payload):
            return 42

        def attach_product_picture(self, product_id, image_path):
            calls["attached"] = (product_id, image_path)

        def add_product_to_shopping_list(self, product_id, amount, best_before_date=""):
            return None

    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/search",
        headers={"Authorization": "Bearer test-api-key"},
        json={"name": "Apfel"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "created_and_added"
    assert calls["attached"] == (42, "/tmp/generated/apfel.png")
