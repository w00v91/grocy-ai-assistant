from grocy_ai_assistant.api import routes


def test_shopping_list_returns_items(client, monkeypatch):
    def fake_get_shopping_list(self):
        return [
            {
                "id": 11,
                "amount": "2",
                "product_name": "Hafermilch",
                "note": "Barista",
                "picture_url": "https://example.org/hafermilch.png",
            }
        ]

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    response = client.get(
        "/api/dashboard/shopping-list",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 11
    assert response.json()[0]["amount"] == "2"
    assert response.json()[0]["product_name"] == "Hafermilch"
    assert response.json()[0]["note"] == "Barista"
    assert response.json()[0]["picture_url"].startswith("/api/dashboard/product-picture?src=")


def test_dashboard_prefills_configured_api_key(client):
    response = client.get("/")

    assert response.status_code == 200
    assert 'const configuredApiKey = "test-api-key";' in response.text
    assert "prompt('Bitte API-Key eingeben:'" not in response.text


def test_dashboard_has_mobile_friendly_layout_rules(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "@media (max-width: 640px)" in response.text
    assert "min-height: 44px;" in response.text
    assert "flex-direction: column;" in response.text


def test_shopping_list_can_be_cleared(client, monkeypatch):
    def fake_clear_shopping_list(self):
        return 3

    monkeypatch.setattr(
        routes.GrocyClient, "clear_shopping_list", fake_clear_shopping_list
    )

    response = client.delete(
        "/api/dashboard/shopping-list/clear",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "removed_items": 3,
        "message": "Einkaufsliste geleert (3 Einträge entfernt).",
    }


def test_shopping_list_builds_proxy_picture_url_from_filename(client, monkeypatch):
    def fake_get_shopping_list(self):
        return [
            {
                "id": 12,
                "amount": "1",
                "product_name": "Nudeln",
                "note": "",
                "picture_file_name": "abc123.jpg",
            }
        ]

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    response = client.get(
        "/api/dashboard/shopping-list",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert "/api/dashboard/product-picture?src=" in response.json()[0]["picture_url"]
    assert "files%2Fproductpictures%2Fabc123.jpg" in response.json()[0]["picture_url"]


def test_dashboard_contains_clear_button(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Einkaufsliste leeren" in response.text
    assert "class='danger-button'" in response.text


def test_dashboard_fallback_serves_ingress_path(client):
    response = client.get("/api/hassio_ingress/71139b3d_grocy_ai_assistant")

    assert response.status_code == 200
    assert "Grocy AI Suche" in response.text


def test_dashboard_fallback_keeps_404_for_unknown_api_paths(client):
    response = client.get("/api/not-a-real-endpoint")

    assert response.status_code == 404


def test_product_picture_proxy_fetches_with_grocy_api_key(client, monkeypatch):
    class FakeResponse:
        content = b"img"
        headers = {"Content-Type": "image/png"}

        def raise_for_status(self):
            return None

    captured = {}

    def fake_requests_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(routes.requests, "get", fake_requests_get)
    response = client.get(
        "/api/dashboard/product-picture",
        params={"src": "http://homeassistant.local:9192/files/productpictures/abc123.jpg"},
    )

    assert response.status_code == 200
    assert response.content == b"img"
    assert response.headers["content-type"].startswith("image/png")
    assert captured["url"] == "http://homeassistant.local:9192/files/productpictures/abc123.jpg"
    assert captured["headers"]["GROCY-API-KEY"] == "test-grocy-key"


def test_product_picture_proxy_rejects_foreign_hosts(client):
    response = client.get(
        "/api/dashboard/product-picture",
        params={"src": "https://example.com/abc.jpg"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Ungültige Bildquelle"


def test_dashboard_contains_darkmode_toggle_in_top_right(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "id='theme-toggle'" in response.text
    assert "right: 1rem;" in response.text
    assert "toggleTheme()" in response.text
    assert "localStorage.setItem(themeStorageKey, nextTheme);" in response.text
