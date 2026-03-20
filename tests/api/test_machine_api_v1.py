from grocy_ai_assistant.api import routes


def test_v1_shopping_list_reuses_dashboard_contract(client, monkeypatch):
    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def get_shopping_list(self):
            return [
                {
                    "id": 5,
                    "amount": "2",
                    "product_id": 9,
                    "product_name": "Milch",
                    "location_name": "Kühlschrank",
                }
            ]

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/v1/shopping-list",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 5,
            "amount": "2",
            "product_id": 9,
            "product_name": "Milch",
            "note": "",
            "picture_url": "",
            "location_name": "Kühlschrank",
            "in_stock": "",
            "best_before_date": "",
            "default_amount": "",
            "calories": "",
            "carbs": "",
            "fat": "",
            "protein": "",
            "sugar": "",
        }
    ]


def test_v1_stock_supports_dashboard_query_parameters(client, monkeypatch):
    captured: dict[str, object] = {}

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def get_storage_products(
            self, location_ids=None, include_all_products=False, search_query=""
        ):
            captured["location_ids"] = location_ids
            captured["include_all_products"] = include_all_products
            captured["search_query"] = search_query
            return [
                {
                    "id": 3,
                    "stock_id": 7,
                    "in_stock": True,
                    "name": "Butter",
                    "location_id": 2,
                    "location_name": "Kühlschrank",
                    "amount": "1",
                    "best_before_date": "2026-03-25",
                }
            ]

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/v1/stock?location_ids=2,4&include_all_products=true&q=but",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert captured == {
        "location_ids": [2, 4],
        "include_all_products": True,
        "search_query": "but",
    }
    assert response.json()[0]["name"] == "Butter"


def test_v1_recipes_accepts_get_query_arguments(client, monkeypatch):
    captured: dict[str, object] = {}

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(self, selected_products, existing_titles):
            return []

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def get_stock_products(self, location_ids=None):
            captured["location_ids"] = location_ids
            return [{"id": 1, "name": "Tomaten"}]

        def get_recipes(self):
            return [
                {
                    "id": 11,
                    "name": "Tomatensuppe",
                    "description": "Warm",
                    "picture_url": "",
                }
            ]

        def get_recipe_ingredients(self, recipe_id):
            return ["Tomaten"]

        def get_missing_recipe_products(self, recipe_id):
            return []

        def find_product_by_name(self, name):
            return None

    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/v1/recipes?product_ids=1,8&location_ids=2&soon_expiring_only=false&expiring_within_days=4",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert captured["location_ids"] == [2]
    assert response.json()["grocy_recipes"][0]["title"] == "Tomatensuppe"


def test_v1_barcode_reuses_dashboard_lookup(client, monkeypatch):
    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_barcode(self, barcode):
            assert barcode == "4008400408400"
            return {"name": "Haferdrink"}

    def raise_timeout(*args, **kwargs):
        raise routes.requests.Timeout("timeout")

    monkeypatch.setattr(routes.requests, "get", raise_timeout)
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/v1/barcode/4008400408400",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["product_name"] == "Haferdrink"
    assert response.json()["source"] == "Grocy"


def test_v1_last_scan_returns_latest_machine_scan_result(client, monkeypatch):
    routes.LAST_SCAN_RESULT["updated_at"] = ""
    routes.LAST_SCAN_RESULT["result"] = None

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def detect_product_from_image(self, image_base64, timeout_seconds=45):
            assert image_base64 == "abc123"
            return {
                "product_name": "Banane",
                "brand": "Bio",
                "hint": "Gelbe Frucht",
            }

    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    scan_response = client.post(
        "/api/v1/scan/image",
        headers={"Authorization": "Bearer test-api-key"},
        json={"image_base64": "abc123"},
    )
    assert scan_response.status_code == 200

    response = client.get(
        "/api/v1/last-scan",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["result"]["product_name"] == "Banane"
    assert payload["updated_at"]
