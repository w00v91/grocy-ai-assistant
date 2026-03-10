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
    assert response.json()[0]["picture_url"].startswith(
        "/api/dashboard/product-picture?src="
    )


def test_dashboard_references_external_template_assets(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "/dashboard-static/dashboard.css" in response.text
    assert "/dashboard-static/dashboard.js" in response.text


def test_dashboard_prefills_configured_api_key(client):
    response = client.get("/")

    assert response.status_code == 200
    assert 'data-configured-api-key="test-api-key"' in response.text
    assert "prompt('Bitte API-Key eingeben:'" not in response.text


def test_dashboard_has_mobile_friendly_layout_rules(client):
    response = client.get("/")

    assert response.status_code == 200
    static_response = client.get("/dashboard-static/dashboard.css")

    assert static_response.status_code == 200
    assert "@media (max-width: 640px)" in static_response.text
    assert "min-height: 44px;" in static_response.text
    assert "flex-direction: column;" in static_response.text


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
    assert (
        "files%2Fproductpictures%2FYWJjMTIzLmpwZw%3D%3D"
        in response.json()[0]["picture_url"]
    )


def test_shopping_list_uses_nested_product_picture_filename(client, monkeypatch):
    def fake_get_shopping_list(self):
        return [
            {
                "id": 13,
                "amount": "1",
                "product_name": "Cookies",
                "note": "",
                "product": {
                    "id": "1",
                    "name": "Cookies",
                    "picture_file_name": "cookies.jpg",
                },
            }
        ]

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    response = client.get(
        "/api/dashboard/shopping-list",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert "/api/dashboard/product-picture?src=" in response.json()[0]["picture_url"]
    assert (
        "files%2Fproductpictures%2FY29va2llcy5qcGc%3D"
        in response.json()[0]["picture_url"]
    )


def test_dashboard_contains_clear_button(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Einkaufsliste leeren" in response.text
    assert "class='danger-button'" in response.text


def test_dashboard_fallback_serves_ingress_path(client):
    ingress_path = "/api/hassio_ingress/71139b3d_grocy_ai_assistant"
    response = client.get(ingress_path)

    assert response.status_code == 200
    assert "Grocy AI Suche" in response.text
    assert f"{ingress_path}/dashboard-static/dashboard.js" in response.text


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
    client.app.state.product_image_cache = None
    response = client.get(
        "/api/dashboard/product-picture",
        params={
            "src": "http://homeassistant.local:9192/files/productpictures/abc123.jpg"
        },
    )

    assert response.status_code == 200
    assert response.content == b"img"
    assert response.headers["content-type"].startswith("image/png")
    assert (
        captured["url"]
        == "http://homeassistant.local:9192/files/productpictures/abc123.jpg"
    )
    assert captured["headers"]["GROCY-API-KEY"] == "test-grocy-key"


def test_product_picture_proxy_rejects_foreign_hosts(client):
    response = client.get(
        "/api/dashboard/product-picture",
        params={"src": "https://example.com/abc.jpg"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Ungültige Bildquelle"


def test_dashboard_handles_network_errors_in_ui(client):
    response = client.get("/")

    assert response.status_code == 200
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "Netzwerk-/Ingress-Fehler" in static_response.text
    assert "parseJsonSafe" in static_response.text


def test_dashboard_uses_relative_api_fallback_when_base_path_missing(client):
    response = client.get("/")

    assert response.status_code == 200
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "function buildApiUrl(path)" in static_response.text
    assert "return normalizedPath.replace(/^\\//, '');" in static_response.text
    assert "fetch(buildApiUrl('/api/dashboard/search')" in static_response.text


def test_dashboard_detects_ingress_prefix_from_location(client):
    response = client.get("/")

    assert response.status_code == 200
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert (
        r"const ingressPrefixMatch = window.location.pathname.match(/^\/api\/hassio_ingress\/[^\/]+/);"
        in static_response.text
    )
    assert "if (ingressPrefix) {" in static_response.text
    assert "return `${ingressPrefix}${normalizedPath}`;" in static_response.text


def test_dashboard_contains_darkmode_toggle_in_top_right(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "id='theme-toggle'" in response.text

    static_response = client.get("/dashboard-static/dashboard.css")
    assert static_response.status_code == 200
    assert "right: 1rem;" in static_response.text
    assert "toggleTheme()" in response.text

    js_response = client.get("/dashboard-static/dashboard.js")
    assert js_response.status_code == 200
    assert "localStorage.setItem(themeStorageKey, nextTheme);" in js_response.text


def test_product_picture_uses_app_cache_when_available(client):
    class FakeCache:
        def get_cached_image(self, src):
            assert (
                src
                == "http://homeassistant.local:9192/files/productpictures/abc123.jpg"
            )
            return b"cached", "image/jpeg"

        def stop(self):
            return None

    client.app.state.product_image_cache = FakeCache()

    response = client.get(
        "/api/dashboard/product-picture",
        params={
            "src": "http://homeassistant.local:9192/files/productpictures/abc123.jpg"
        },
    )

    assert response.status_code == 200
    assert response.content == b"cached"


def test_refresh_product_picture_cache_endpoint(client):
    class FakeCache:
        def refresh_all_product_images(self):
            return 7

        def stop(self):
            return None

    client.app.state.product_image_cache = FakeCache()

    response = client.post(
        "/api/dashboard/product-picture-cache/refresh",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True, "refreshed_images": 7}
