from datetime import date, timedelta
import requests
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
                "sugar": "4.8",
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
    assert response.json()[0]["sugar"] == "4.8"
    assert response.json()[0]["picture_url"].startswith(
        "/api/dashboard/product-picture?src="
    )


def test_dashboard_references_external_template_assets(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "/dashboard-static/dashboard.css" in response.text
    assert "/dashboard-static/dashboard.js" in response.text


def test_dashboard_exposes_home_assistant_theme_bridge_metadata(client):
    response = client.get("/")

    assert response.status_code == 200
    assert 'data-theme-source="home-assistant-parent"' in response.text
    assert 'data-theme-bridge-mode="same-origin-css-vars"' in response.text
    assert (
        'data-ha-theme-vars="primary-background-color,secondary-background-color,card-background-color,primary-text-color,secondary-text-color,divider-color,primary-color,error-color,success-color"'
        in response.text
    )


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


def test_dashboard_has_clear_search_input_button(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "id='clear-name'" in response.text
    assert "onclick='clearSearchInput()'" in response.text

    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "function clearSearchInput()" in static_response.text
    assert "updateClearButtonVisibility();" in static_response.text


def test_dashboard_places_variant_section_below_search(client):
    response = client.get("/")

    assert response.status_code == 200
    search_pos = response.text.index("Grocy AI Suche")
    variant_pos = response.text.index("id='variant-section'")
    recipe_pos = response.text.index("Rezeptvorschläge")

    assert search_pos < variant_pos < recipe_pos


def test_dashboard_does_not_autoload_variants(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "\nloadVariants();\nloadStockProducts();" not in static_response.text
    assert "list.innerHTML = '';" in static_response.text


def test_dashboard_does_not_autoload_recipe_suggestions_on_recipe_tab_open(client):
    response = client.get("/")
    static_response = client.get("/dashboard-static/dashboard.js")

    assert response.status_code == 200
    assert static_response.status_code == 200
    assert "onclick='loadRecipeSuggestions()'" in response.text
    assert (
        "Bestand geladen. Lade Rezeptvorschläge bei Bedarf manuell."
        in static_response.text
    )
    assert (
        "Bestand aktualisiert. Lade Rezeptvorschläge bei Bedarf manuell."
        in static_response.text
    )


def test_dashboard_places_recipe_lists_directly_below_recipe_heading(client):
    response = client.get("/")

    assert response.status_code == 200
    heading_pos = response.text.index("<h2>Rezeptvorschläge</h2>")
    columns_pos = response.text.index("<div class='recipe-columns'>")
    filter_pos = response.text.index("<div class='stock-filters-layout'>")

    assert heading_pos < columns_pos < filter_pos


def test_dashboard_limits_displayed_recipe_amount_per_source(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "const GROCY_RECIPE_DISPLAY_LIMIT = 3;" in static_response.text
    assert "const AI_RECIPE_DISPLAY_LIMIT = 3;" in static_response.text
    assert ".slice(0, GROCY_RECIPE_DISPLAY_LIMIT)" in static_response.text
    assert ".slice(0, AI_RECIPE_DISPLAY_LIMIT)" in static_response.text


def test_dashboard_preloads_recipe_suggestions_on_startup(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "function preloadRecipeSuggestionsOnStartup()" in static_response.text
    assert "preloadRecipeSuggestionsOnStartup();" in static_response.text


def test_dashboard_loads_initial_recipe_suggestions_once_after_stock_load(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "hasLoadedInitialSuggestions" in static_response.text
    assert (
        "if (!hasStockChanged && !recipeState.hasLoadedInitialSuggestions)"
        in static_response.text
    )
    assert (
        "await loadRecipeSuggestions({ usePrefetchedCache: true });"
        in static_response.text
    )
    assert (
        "const usePrefetchedCache = Boolean(options.usePrefetchedCache);"
        in static_response.text
    )
    assert (
        "const selectedIds = usePrefetchedCache ? [] : getSelectedProductIds();"
        in static_response.text
    )


def test_dashboard_recipes_use_normalized_image_sources(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert (
        'class="recipe-thumb" src="${toImageSource(item.picture_url)}"'
        in static_response.text
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


def test_dashboard_fallback_serves_token_path(client):
    token_path = "/DSjkRSg2MQhfRCPVJYCvOW2o9DXs2ZwTf_Lm8z3CytA"
    response = client.get(token_path)

    assert response.status_code == 200
    assert "Grocy AI Suche" in response.text
    assert f"{token_path}/dashboard-static/dashboard.js" in response.text


def test_dashboard_uses_ingress_header_for_static_assets(client):
    ingress_path = "/DSjkRSg2MQhfRCPVJYCvOW2o9DXs2ZwTf_Lm8z3CytA"
    response = client.get("/", headers={"x-ingress-path": ingress_path})

    assert response.status_code == 200
    assert f"{ingress_path}/dashboard-static/dashboard.js" in response.text


def test_dashboard_uses_forwarded_prefix_header_for_static_assets(client):
    ingress_path = "/DSjkRSg2MQhfRCPVJYCvOW2o9DXs2ZwTf_Lm8z3CytA"
    response = client.get("/", headers={"x-forwarded-prefix": ingress_path})

    assert response.status_code == 200
    assert f"{ingress_path}/dashboard-static/dashboard.js" in response.text


def test_dashboard_uses_ingress_header_for_api_base_path(client):
    ingress_path = "/api/hassio_ingress/71139b3d_grocy_ai_assistant"
    response = client.get("/", headers={"x-ingress-path": ingress_path})

    assert response.status_code == 200
    assert f'data-api-base-path="{ingress_path}"' in response.text


def test_dashboard_fallback_uses_empty_api_base_path_for_token_path(client):
    token_path = "/DSjkRSg2MQhfRCPVJYCvOW2o9DXs2ZwTf_Lm8z3CytA"
    response = client.get(token_path)

    assert response.status_code == 200
    assert 'data-api-base-path=""' in response.text


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
        == "http://homeassistant.local:9192/files/productpictures/abc123.jpg?best_fit_width=96&best_fit_height=96&force_serve_as=picture"
    )
    assert captured["headers"]["GROCY-API-KEY"] == "test-grocy-key"


def test_product_picture_proxy_supports_mobile_size(client, monkeypatch):
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
            "src": "http://homeassistant.local:9192/files/productpictures/abc123.jpg",
            "size": "mobile",
        },
    )

    assert response.status_code == 200
    assert response.content == b"img"
    assert response.headers["cache-control"] == "public, max-age=86400"
    assert (
        captured["url"]
        == "http://homeassistant.local:9192/files/productpictures/abc123.jpg?best_fit_width=64&best_fit_height=64&force_serve_as=picture"
    )
    assert captured["headers"]["GROCY-API-KEY"] == "test-grocy-key"


def test_product_picture_proxy_uses_files_fallback_on_404(client, monkeypatch):
    class NotFoundResponse:
        status_code = 404

    class FakeResponse:
        content = b"img"
        headers = {"Content-Type": "image/jpeg"}

        def raise_for_status(self):
            return None

    calls = []

    def fake_requests_get(url, headers, timeout):
        calls.append(url)

        class FirstAttempt:
            def raise_for_status(self_inner):
                if url.startswith("http://homeassistant.local:9192/api/files/"):
                    error = routes.requests.HTTPError("not found")
                    error.response = NotFoundResponse()
                    raise error
                return None

            content = b"img"
            headers = {"Content-Type": "image/jpeg"}

        if url.startswith("http://homeassistant.local:9192/api/files/"):
            return FirstAttempt()
        return FakeResponse()

    monkeypatch.setattr(routes.requests, "get", fake_requests_get)
    client.app.state.product_image_cache = None

    response = client.get(
        "/api/dashboard/product-picture",
        params={
            "src": "http://homeassistant.local:9192/api/files/recipepictures/test.jpg?force_serve_as=picture"
        },
    )

    assert response.status_code == 200
    assert response.content == b"img"
    assert calls == [
        "http://homeassistant.local:9192/api/files/recipepictures/test.jpg?force_serve_as=picture&best_fit_width=96&best_fit_height=96",
        "http://homeassistant.local:9192/files/recipepictures/test.jpg?force_serve_as=picture&best_fit_width=96&best_fit_height=96",
    ]


def test_product_picture_proxy_decodes_encoded_query_in_src_path(client, monkeypatch):
    class FakeResponse:
        content = b"img"
        headers = {"Content-Type": "image/jpeg"}

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
            "src": "http://homeassistant.local:9192/api/files/recipepictures/test.jpg%3Fforce_serve_as%3Dpicture"
        },
    )

    assert response.status_code == 200
    assert response.content == b"img"
    assert (
        captured["url"]
        == "http://homeassistant.local:9192/api/files/recipepictures/test.jpg?force_serve_as=picture&best_fit_width=96&best_fit_height=96"
    )


def test_product_picture_proxy_rejects_foreign_hosts(client):
    response = client.get(
        "/api/dashboard/product-picture",
        params={"src": "https://example.com/abc.jpg"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert (
        payload.get("detail") == "Ungültige Bildquelle"
        or payload.get("error", {}).get("message") == "Ungültige Bildquelle"
    )


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


def test_dashboard_syncs_home_assistant_theme_instead_of_manual_darkmode_toggle(
    client,
):
    response = client.get("/")

    assert response.status_code == 200
    assert "id='theme-badge'" in response.text
    assert "HA Theme" in response.text
    assert "toggleTheme()" not in response.text

    static_response = client.get("/dashboard-static/dashboard.css")
    assert static_response.status_code == 200
    assert "position: relative;" in static_response.text
    assert "--bg-primary: var(--ha-primary-background-color" in static_response.text
    assert "--accent-primary: var(--ha-primary-color" in static_response.text
    assert ":root[data-theme='dark']" not in static_response.text

    js_response = client.get("/dashboard-static/dashboard.js")
    assert js_response.status_code == 200
    assert "function syncThemeFromHomeAssistant()" in js_response.text
    assert "window.parent.getComputedStyle(element)" in js_response.text
    assert (
        "HA_THEME_MESSAGE_TYPE = 'grocy-ai-assistant:ha-theme-sync'" in js_response.text
    )
    assert "localStorage.setItem(themeStorageKey, nextTheme);" not in js_response.text


def test_product_picture_uses_app_cache_when_available(client):
    class FakeCache:
        def get_cached_image(self, src):
            assert (
                src
                == "http://homeassistant.local:9192/files/productpictures/abc123.jpg?best_fit_width=96&best_fit_height=96&force_serve_as=picture"
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


def test_stock_products_endpoint_returns_items(client, monkeypatch):
    def fake_get_stock_products(self):
        return [
            {
                "id": 1,
                "name": "Milch",
                "location_name": "Kühlschrank",
                "amount": "1",
                "best_before_date": "2026-01-02",
            }
        ]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )

    response = client.get(
        "/api/dashboard/stock-products",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Milch"
    assert response.json()[0]["best_before_date"] == "2026-01-02"


def test_stock_products_endpoint_supports_include_all_products(client, monkeypatch):
    called = {}

    def fake_get_storage_products(
        self, location_ids=None, include_all_products=False, search_query=""
    ):
        called["search_query"] = search_query
        called["location_ids"] = location_ids
        called["include_all_products"] = include_all_products
        return [
            {
                "id": 1,
                "name": "Milch",
                "in_stock": False,
                "location_name": "Kühlschrank",
                "amount": "0",
                "best_before_date": "",
            }
        ]

    monkeypatch.setattr(
        routes.GrocyClient, "get_storage_products", fake_get_storage_products
    )

    response = client.get(
        "/api/dashboard/stock-products?include_all_products=true&location_ids=2&q=mil",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert called["location_ids"] == [2]
    assert called["include_all_products"] is True
    assert called["search_query"] == "mil"
    assert response.json()[0]["in_stock"] is False


def test_recipe_suggestions_prioritize_grocy_then_ai(client, monkeypatch):
    def fake_get_stock_products(self):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"},
            {"id": 2, "name": "Nudeln", "location_name": "Vorrat", "amount": "1"},
        ]

    def fake_get_recipes(self):
        return [
            {"id": 10, "name": "Tomaten Pasta", "description": "Pasta kochen"},
            {"id": 11, "name": "Gemüsepfanne", "description": "Anbraten"},
        ]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            assert selected_products == ["Tomate"]
            assert "Tomaten Pasta" in existing_recipe_titles
            return [
                {
                    "title": "Tomaten-Suppe",
                    "reason": "Tomate ist vorhanden",
                    "preparation": "Tomaten schneiden und köcheln.",
                }
            ]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "get_recipe_ingredients",
        lambda self, recipe_id: ["200 g Tomate"],
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers={"Authorization": "Bearer test-api-key"},
        json={"product_ids": [1]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_products"] == ["Tomate"]
    assert payload["grocy_recipes"][0]["source"] == "grocy"
    assert payload["grocy_recipes"][0]["title"] == "Tomaten Pasta"
    assert payload["grocy_recipes"][0]["recipe_id"] == 10
    assert payload["grocy_recipes"][0]["preparation"] == "Pasta kochen"
    assert payload["grocy_recipes"][0]["ingredients"] == ["200 g Tomate"]
    assert payload["ai_recipes"][0]["source"] == "ai"
    assert payload["ai_recipes"][0]["preparation"] == "Tomaten schneiden und köcheln."
    assert payload["ai_recipes"][0]["ingredients"] == ["1 Portion Tomate"]


def test_recipe_suggestions_uses_stock_products_when_selection_is_empty(
    client, monkeypatch
):
    def fake_get_stock_products(self):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"},
            {"id": 2, "name": "Nudeln", "location_name": "Vorrat", "amount": "1"},
        ]

    def fake_get_recipes(self):
        return [{"id": 10, "name": "Tomaten Pasta", "description": "Pasta kochen"}]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            assert selected_products == ["Tomate", "Nudeln"]
            return [{"title": "Tomaten-Nudel-Pfanne", "reason": "Vorrat passt"}]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "get_recipe_ingredients",
        lambda self, recipe_id: ["100 g Tomate"],
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers={"Authorization": "Bearer test-api-key"},
        json={"product_ids": []},
    )

    assert response.status_code == 200
    assert response.json()["selected_products"] == ["Tomate", "Nudeln"]


def test_recipe_suggestions_returns_empty_when_no_stock_products(client, monkeypatch):
    def fake_get_stock_products(self, location_ids=None):
        assert location_ids == [999]
        return []

    def fake_get_recipes(self):
        return [{"id": 10, "name": "Tomaten Pasta", "description": "Pasta kochen"}]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            raise AssertionError("KI sollte bei leerem Bestand nicht aufgerufen werden")

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient, "get_recipe_ingredients", lambda self, recipe_id: []
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers={"Authorization": "Bearer test-api-key"},
        json={"product_ids": [], "location_ids": [999]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "selected_products": [],
        "grocy_recipes": [],
        "ai_recipes": [],
    }


def test_recipe_suggestions_soon_expiring_handles_string_ids_and_datetime_dates(
    client, monkeypatch
):
    def fake_get_stock_products(self, location_ids=None):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"},
            {"id": 2, "name": "Nudeln", "location_name": "Vorrat", "amount": "1"},
        ]

    def fake_get_stock_entries(self, location_ids=None):
        soon_1 = (date.today() + timedelta(days=1)).isoformat()
        soon_2 = (date.today() + timedelta(days=2)).isoformat()
        return [
            {
                "product_id": "1",
                "best_before_date": f"{soon_1} 00:00:00",
            },
            {
                "product_id": "2",
                "best_before_date": f"{soon_2}T12:34:56",
            },
        ]

    def fake_get_recipes(self):
        return [{"id": 10, "name": "Tomaten Pasta", "description": "Pasta kochen"}]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            assert selected_products == ["Tomate", "Nudeln"]
            return [{"title": "Tomaten-Nudel-Pfanne", "reason": "Vorrat passt"}]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "get_recipe_ingredients",
        lambda self, recipe_id: ["100 g Tomate"],
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers={"Authorization": "Bearer test-api-key"},
        json={"product_ids": [], "soon_expiring_only": True, "expiring_within_days": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_products"] == ["Tomate", "Nudeln"]


def test_recipe_suggestions_generates_fallback_when_ai_returns_nothing(
    client, monkeypatch
):
    def fake_get_stock_products(self, location_ids=None):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"}
        ]

    def fake_get_recipes(self):
        return [
            {
                "id": 10,
                "name": "Tomaten Pasta",
                "picture_url": "/img/tomaten-pasta.jpg",
                "description": "Pasta kochen",
            }
        ]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            return []

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "get_recipe_ingredients",
        lambda self, recipe_id: ["250 g Tomate"],
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers={"Authorization": "Bearer test-api-key"},
        json={"product_ids": [1]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["grocy_recipes"][0]["picture_url"].startswith(
        "/api/dashboard/product-picture?src="
    )
    assert (
        "http%3A%2F%2Fhomeassistant.local%3A9192%2Fimg%2Ftomaten-pasta.jpg"
        in payload["grocy_recipes"][0]["picture_url"]
    )
    assert len(payload["ai_recipes"]) == 3
    assert payload["ai_recipes"][0]["title"]
    assert payload["ai_recipes"][0]["ingredients"]


def test_recipe_suggestions_fills_up_to_three_ai_recipes_when_ai_returns_only_one(
    client, monkeypatch
):
    def fake_get_stock_products(self, location_ids=None):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"}
        ]

    def fake_get_recipes(self):
        return [
            {
                "id": 10,
                "name": "Tomaten Pasta",
                "picture_url": "/img/tomaten-pasta.jpg",
            },
            {
                "id": 11,
                "name": "Tomaten Suppe",
                "picture_url": "/img/tomaten-suppe.jpg",
            },
            {"id": 12, "name": "Tomaten Reis", "picture_url": "/img/tomaten-reis.jpg"},
            {
                "id": 13,
                "name": "Tomaten Auflauf",
                "picture_url": "/img/tomaten-auflauf.jpg",
            },
        ]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            return [
                {
                    "title": "Tomaten-Curry",
                    "reason": "Passt zu Tomate",
                    "ingredients": ["2 Tomaten"],
                }
            ]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "get_recipe_ingredients",
        lambda self, recipe_id: ["300 g Tomate"],
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers={"Authorization": "Bearer test-api-key"},
        json={"product_ids": [1]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["grocy_recipes"]) == 3
    assert len(payload["ai_recipes"]) == 3
    assert payload["ai_recipes"][0]["title"] == "Tomaten-Curry"


def test_add_missing_recipe_products_adds_to_shopping_list(client, monkeypatch):
    captured = []

    def fake_get_missing_recipe_products(self, recipe_id):
        assert recipe_id == 10
        return [{"id": 1, "name": "Milch"}, {"id": 2, "name": "Nudeln"}]

    def fake_add_product_to_shopping_list(self, product_id, amount=1):
        captured.append((product_id, amount))

    monkeypatch.setattr(
        routes.GrocyClient,
        "get_missing_recipe_products",
        fake_get_missing_recipe_products,
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "add_product_to_shopping_list",
        fake_add_product_to_shopping_list,
    )

    response = client.post(
        "/api/dashboard/recipe/10/add-missing",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["added_items"] == 2
    assert captured == [(1, 1), (2, 1)]


def test_dashboard_contains_recipe_section(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Rezeptvorschläge" in response.text
    assert "recipe-modal-ingredients" in response.text

    js_response = client.get("/dashboard-static/dashboard.js")
    assert js_response.status_code == 200
    assert "loadRecipeSuggestions" in js_response.text
    assert "/api/dashboard/recipe-suggestions" in js_response.text
    assert "recipe-add-missing-button" in response.text
    assert (
        "/api/dashboard/recipe/${activeRecipeItem.recipe_id}/add-missing"
        in js_response.text
    )


def test_dashboard_contains_complete_button(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Einkauf abschließen" in response.text
    assert "class='success-button'" in response.text


def test_dashboard_uses_matching_complete_item_endpoint(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert (
        "/api/dashboard/shopping-list/item/${shoppingListId}/complete"
        in static_response.text
    )
    assert (
        "/api/dashboard/shopping-list/${shoppingListId}/complete"
        not in static_response.text
    )
    assert (
        "/api/dashboard/shopping-list/item/${shoppingListId}/amount/increment"
        in static_response.text
    )


def test_dashboard_notification_event_labels_declared_once(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert static_response.text.count("const NOTIFICATION_EVENT_LABELS = {") == 1


def test_dashboard_swipe_actions_match_labels(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "if (deltaX <= -commitDistance)" in static_response.text
    assert "await purchaseShoppingItem(shoppingListId);" in static_response.text
    assert "if (deltaX >= commitDistance)" in static_response.text
    assert "await removeShoppingItem(shoppingListId);" in static_response.text


def test_dashboard_amount_save_closes_shopping_modal(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "async function saveShoppingAmountFromModal()" in static_response.text
    assert "await closeShoppingItemDetails();" in static_response.text


def test_shopping_list_item_can_be_deleted(client, monkeypatch):
    captured = {}

    def fake_get_shopping_list(self):
        return [{"id": 42, "amount": "2"}]

    def fake_delete_shopping_list_item(self, shopping_list_id, amount="1"):
        captured["shopping_list_id"] = shopping_list_id
        captured["amount"] = amount

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        routes.GrocyClient, "delete_shopping_list_item", fake_delete_shopping_list_item
    )
    response = client.delete(
        "/api/dashboard/shopping-list/item/42",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert captured["shopping_list_id"] == 42
    assert response.json()["success"] is True
    assert captured["amount"] == "2"


def test_shopping_list_item_note_can_be_updated(client, monkeypatch):
    captured = {}

    def fake_get_shopping_list(self):
        return [{"id": 42, "amount": "2", "best_before_date": "2026-12-31"}]

    def fake_update_shopping_list_item_note(
        self, shopping_list_id, note, current_best_before_date=""
    ):
        captured["shopping_list_id"] = shopping_list_id
        captured["note"] = note
        captured["current_best_before_date"] = current_best_before_date

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        routes.GrocyClient,
        "update_shopping_list_item_note",
        fake_update_shopping_list_item_note,
    )

    response = client.put(
        "/api/dashboard/shopping-list/item/42/note",
        headers={"Authorization": "Bearer test-api-key"},
        json={"note": "Nur Bio kaufen"},
    )

    assert response.status_code == 200
    assert captured == {
        "shopping_list_id": 42,
        "note": "Nur Bio kaufen",
        "current_best_before_date": "2026-12-31",
    }
    assert response.json()["success"] is True


def test_shopping_list_item_best_before_date_can_be_updated(client, monkeypatch):
    captured = {}

    def fake_get_shopping_list(self):
        return [{"id": 42, "amount": "2", "note": "dringend"}]

    def fake_update_shopping_list_item_best_before_date(
        self, shopping_list_id, best_before_date, current_note=""
    ):
        captured["shopping_list_id"] = shopping_list_id
        captured["best_before_date"] = best_before_date
        captured["current_note"] = current_note

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        routes.GrocyClient,
        "update_shopping_list_item_best_before_date",
        fake_update_shopping_list_item_best_before_date,
    )

    response = client.put(
        "/api/dashboard/shopping-list/item/42/best-before",
        headers={"Authorization": "Bearer test-api-key"},
        json={"best_before_date": "2026-12-31"},
    )

    assert response.status_code == 200
    assert captured == {
        "shopping_list_id": 42,
        "best_before_date": "2026-12-31",
        "current_note": "dringend",
    }
    assert response.json()["success"] is True


def test_shopping_list_item_best_before_date_update_rejects_missing_entry(
    client, monkeypatch
):
    def fake_get_shopping_list(self):
        return []

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)

    response = client.put(
        "/api/dashboard/shopping-list/item/42/best-before",
        headers={"Authorization": "Bearer test-api-key"},
        json={"best_before_date": "2026-12-31"},
    )

    assert response.status_code == 404


def test_shopping_list_item_best_before_date_can_be_reset(client, monkeypatch):
    captured = {}

    def fake_get_shopping_list(self):
        return [
            {
                "id": 42,
                "product_id": 7,
                "default_amount": "5",
                "note": "dringend",
            }
        ]

    def fake_update_shopping_list_item_best_before_date(
        self, shopping_list_id, best_before_date, current_note=""
    ):
        captured["updated"] = {
            "shopping_list_id": shopping_list_id,
            "best_before_date": best_before_date,
            "current_note": current_note,
        }

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        routes.GrocyClient,
        "update_shopping_list_item_best_before_date",
        fake_update_shopping_list_item_best_before_date,
    )

    response = client.post(
        "/api/dashboard/shopping-list/item/42/best-before/reset",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert captured == {
        "updated": {
            "shopping_list_id": 42,
            "best_before_date": "",
            "current_note": "dringend",
        },
    }
    assert response.json() == {
        "success": True,
        "message": "MHD für Eintrag 42 zurückgesetzt.",
        "best_before_date": "",
    }


def test_shopping_list_can_be_completed(client, monkeypatch):
    def fake_complete_shopping_list(self):
        return 5

    monkeypatch.setattr(
        routes.GrocyClient,
        "complete_shopping_list",
        fake_complete_shopping_list,
    )

    response = client.post(
        "/api/dashboard/shopping-list/complete",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "completed_items": 5,
        "message": "Einkauf abgeschlossen (5 Einträge als eingekauft markiert).",
    }


def test_shopping_list_item_amount_can_be_updated(client, monkeypatch):
    captured = {}

    def fake_get_shopping_list(self):
        return [{"id": 9, "amount": "3"}]

    def fake_update_shopping_list_item_amount(self, shopping_list_id, amount):
        captured["shopping_list_id"] = shopping_list_id
        captured["amount"] = amount

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        routes.GrocyClient,
        "update_shopping_list_item_amount",
        fake_update_shopping_list_item_amount,
    )

    response = client.put(
        "/api/dashboard/shopping-list/item/9/amount",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 4.5},
    )

    assert response.status_code == 200
    assert captured == {
        "shopping_list_id": 9,
        "amount": "4.5",
    }
    assert response.json()["amount"] == "4.5"


def test_shopping_list_item_amount_can_be_incremented(client, monkeypatch):
    captured = {}

    def fake_get_shopping_list(self):
        return [{"id": 9, "amount": "3"}]

    def fake_update_shopping_list_item_amount(self, shopping_list_id, amount):
        captured["shopping_list_id"] = shopping_list_id
        captured["amount"] = amount

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        routes.GrocyClient,
        "update_shopping_list_item_amount",
        fake_update_shopping_list_item_amount,
    )

    response = client.post(
        "/api/dashboard/shopping-list/item/9/amount/increment",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert captured == {
        "shopping_list_id": 9,
        "amount": "4",
    }
    assert response.json()["amount"] == "4"


def test_shopping_list_item_can_be_completed(client, monkeypatch):
    captured = {}

    def fake_get_shopping_list(self):
        return [
            {"id": 9, "product_id": 11, "amount": "3", "best_before_date": "2026-12-31"}
        ]

    def fake_complete_shopping_list_item(
        self, shopping_list_id, product_id, amount="1", best_before_date=""
    ):
        captured["shopping_list_id"] = shopping_list_id
        captured["product_id"] = product_id
        captured["amount"] = amount
        captured["best_before_date"] = best_before_date

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        routes.GrocyClient,
        "complete_shopping_list_item",
        fake_complete_shopping_list_item,
    )

    response = client.post(
        "/api/dashboard/shopping-list/item/9/complete",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert captured == {
        "shopping_list_id": 9,
        "product_id": 11,
        "amount": "3",
        "best_before_date": "2026-12-31",
    }


def test_shopping_list_item_can_be_completed_with_legacy_endpoint(client, monkeypatch):
    captured = {}

    def fake_get_shopping_list(self):
        return [
            {"id": 9, "product_id": 11, "amount": "3", "best_before_date": "2026-12-31"}
        ]

    def fake_complete_shopping_list_item(
        self, shopping_list_id, product_id, amount="1", best_before_date=""
    ):
        captured["shopping_list_id"] = shopping_list_id
        captured["product_id"] = product_id
        captured["amount"] = amount
        captured["best_before_date"] = best_before_date

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        routes.GrocyClient,
        "complete_shopping_list_item",
        fake_complete_shopping_list_item,
    )

    response = client.post(
        "/api/dashboard/shopping-list/9/complete",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert captured == {
        "shopping_list_id": 9,
        "product_id": 11,
        "amount": "3",
        "best_before_date": "2026-12-31",
    }


def test_dashboard_shows_activity_spinner_in_header(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "id='activity-spinner'" in response.text

    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "function withBusyState(callback)" in static_response.text


def test_dashboard_renders_location_dropdown_filters(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert '<details class="location-dropdown">' in static_response.text
    assert "Lagerstandorte auswählen" in static_response.text


def test_dashboard_contains_scanner_modal_trigger(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "id='tab-scanner'" in response.text
    assert "id='open-scanner-modal-button'" in response.text
    assert "openScannerModal()" in response.text
    assert "id='scanner-modal'" in response.text
    assert "id='scanner-create-product-button'" in response.text


def test_dashboard_exposes_scanner_logic_in_js(client):
    static_response = client.get("/dashboard-static/dashboard.js")

    assert static_response.status_code == 200
    assert "function startBarcodeScanner()" in static_response.text
    assert "BarcodeDetector" in static_response.text
    assert "function lookupBarcode(barcode)" in static_response.text
    assert "function createProductFromScannerResult()" in static_response.text


def test_dashboard_barcode_lookup_returns_product_data(client, monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "status": 1,
                "product": {
                    "product_name": "Haferdrink",
                    "brands": "Oatly",
                    "quantity": "1 l",
                    "ingredients_text_de": "Wasser, Hafer",
                    "nutrition_grades": "b",
                },
            }

    def fake_requests_get(url, timeout, headers):
        assert "0123456789012" in url
        assert timeout == 8
        assert headers["User-Agent"] == "grocy-ai-assistant/scan-tab"
        return FakeResponse()

    monkeypatch.setattr(routes.requests, "get", fake_requests_get)

    response = client.get(
        "/api/dashboard/barcode/0123456789012",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "barcode": "0123456789012",
        "found": True,
        "product_name": "Haferdrink",
        "brand": "Oatly",
        "quantity": "1 l",
        "ingredients_text": "Wasser, Hafer",
        "nutrition_grade": "B",
        "source": "OpenFoodFacts",
    }


def test_dashboard_barcode_lookup_returns_not_found(client, monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"status": 0}

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_barcode(self, barcode):
            assert barcode == "4008400408400"
            return None

    monkeypatch.setattr(routes.requests, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/dashboard/barcode/4008400408400",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["found"] is False


def test_dashboard_barcode_lookup_falls_back_to_grocy(client, monkeypatch):
    class FakeOffResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"status": 0}

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_barcode(self, barcode):
            assert barcode == "4008400408400"
            return {"id": 5, "name": "Hausmarke Pasta"}

    monkeypatch.setattr(
        routes.requests, "get", lambda *args, **kwargs: FakeOffResponse()
    )
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/dashboard/barcode/4008400408400",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "barcode": "4008400408400",
        "found": True,
        "product_name": "Hausmarke Pasta",
        "brand": "",
        "quantity": "",
        "ingredients_text": "",
        "nutrition_grade": "",
        "source": "Grocy",
    }


def test_dashboard_barcode_lookup_returns_not_found_on_off_timeout(client, monkeypatch):
    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def find_product_by_barcode(self, barcode):
            assert barcode == "4008400408400"
            return None

    def fake_requests_get(*args, **kwargs):
        raise requests.ReadTimeout("timed out")

    monkeypatch.setattr(routes.requests, "get", fake_requests_get)
    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.get(
        "/api/dashboard/barcode/4008400408400",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "barcode": "4008400408400",
        "found": False,
        "product_name": "",
        "brand": "",
        "quantity": "",
        "ingredients_text": "",
        "nutrition_grade": "",
        "source": "OpenFoodFacts",
    }


def test_dashboard_barcode_lookup_normalizes_ai_gtin_for_off(client, monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "status": 1,
                "product": {
                    "product_name": "Testprodukt",
                },
            }

    def fake_requests_get(url, timeout, headers):
        assert "4008400408400" in url
        assert "010400840040840017" not in url
        assert timeout == 8
        assert headers["User-Agent"] == "grocy-ai-assistant/scan-tab"
        return FakeResponse()

    monkeypatch.setattr(routes.requests, "get", fake_requests_get)

    response = client.get(
        "/api/dashboard/barcode/010400840040840017",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["barcode"] == "4008400408400"
    assert response.json()["found"] is True


def test_normalize_barcode_for_lookup_prefers_known_lengths():
    assert (
        routes._normalize_barcode_for_lookup("01 04008400408400 17") == "4008400408400"
    )
    assert routes._normalize_barcode_for_lookup("123456789012") == "123456789012"
    assert routes._normalize_barcode_for_lookup("00123456789012") == "00123456789012"


def test_dashboard_barcode_lookup_tries_upc_and_ean_variant(client, monkeypatch):
    class FakeResponse:
        def __init__(self, status):
            self.status_code = 200
            self._status = status

        def json(self):
            if self._status == 1:
                return {
                    "status": 1,
                    "product": {
                        "product_name": "Cola",
                        "brands": "Acme",
                    },
                }
            return {"status": 0}

    requested_codes = []

    def fake_requests_get(url, timeout, headers):
        requested_codes.append(url.split("/product/")[1].split(".json")[0])
        if requested_codes[-1] == "0049300436133":
            return FakeResponse(1)
        return FakeResponse(0)

    monkeypatch.setattr(routes.requests, "get", fake_requests_get)

    response = client.get(
        "/api/dashboard/barcode/049300436133",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert requested_codes == ["049300436133", "0049300436133"]
    assert response.json()["found"] is True
    assert response.json()["barcode"] == "0049300436133"


def test_dashboard_barcode_lookup_rejects_invalid_barcode(client):
    response = client.get(
        "/api/dashboard/barcode/abc",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 400


def test_recipe_suggestions_uses_prefetched_cache_when_stock_unchanged(
    client, monkeypatch
):
    def fake_get_stock_products(self, location_ids=None):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"}
        ]

    class FailDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            raise AssertionError("KI darf bei Cache-Hit nicht aufgerufen werden")

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes, "IngredientDetector", FailDetector)

    client.app.state.recipe_suggestion_cache = {
        "location_ids": [],
        "stock_signature": routes._build_stock_signature(fake_get_stock_products(None)),
        "response": {
            "selected_products": ["Tomate"],
            "grocy_recipes": [
                {
                    "recipe_id": 10,
                    "title": "Tomaten Pasta",
                    "source": "grocy",
                    "reason": "Passt",
                    "preparation": "Kochen",
                    "ingredients": [],
                    "picture_url": "",
                    "missing_products": [],
                }
            ],
            "ai_recipes": [],
        },
    }

    response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers={"Authorization": "Bearer test-api-key"},
        json={"product_ids": [], "location_ids": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_products"] == ["Tomate"]
    assert payload["grocy_recipes"][0]["title"] == "Tomaten Pasta"


def test_recipe_suggestions_caches_soon_expiring_requests(client, monkeypatch):
    call_count = {"detector": 0}

    def fake_get_stock_products(self, location_ids=None):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"},
            {"id": 2, "name": "Nudeln", "location_name": "Vorrat", "amount": "1"},
        ]

    def fake_get_stock_entries(self, location_ids=None):
        soon_1 = (date.today() + timedelta(days=1)).isoformat()
        soon_2 = (date.today() + timedelta(days=2)).isoformat()
        return [
            {"product_id": 1, "best_before_date": soon_1},
            {"product_id": 2, "best_before_date": soon_2},
        ]

    def fake_get_recipes(self):
        return [{"id": 10, "name": "Tomaten Pasta", "description": "Pasta kochen"}]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            call_count["detector"] += 1
            return [{"title": "Tomaten-Nudel-Pfanne", "reason": "Vorrat passt"}]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "get_recipe_ingredients",
        lambda self, recipe_id: ["100 g Tomate"],
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    headers = {"Authorization": "Bearer test-api-key"}
    payload = {"product_ids": [], "soon_expiring_only": True, "expiring_within_days": 3}

    first_response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers=headers,
        json=payload,
    )
    second_response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers=headers,
        json=payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert call_count["detector"] == 1
    assert second_response.json()["selected_products"] == ["Tomate", "Nudeln"]


def test_prefetch_initial_recipe_suggestions_returns_cache_payload(
    monkeypatch, test_settings
):
    def fake_get_stock_products(self, location_ids=None):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"}
        ]

    def fake_get_recipes(self):
        return [{"id": 10, "name": "Tomaten Pasta", "description": "Pasta kochen"}]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            return [{"title": "Tomatensalat", "reason": "Tomate vorhanden"}]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "get_recipe_ingredients",
        lambda self, recipe_id: ["120 g Tomate"],
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    prefetched = routes.prefetch_initial_recipe_suggestions(test_settings)

    assert prefetched is not None
    entry = prefetched["entries"][0]
    assert entry["stock_signature"] == routes._build_stock_signature(
        fake_get_stock_products(None)
    )
    assert entry["selected_ids"] == []
    assert entry["soon_expiring_only"] is False
    assert entry["response"]["selected_products"] == ["Tomate"]
    assert entry["response"]["grocy_recipes"][0]["title"] == "Tomaten Pasta"


def test_dashboard_scanner_contains_llava_controls(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "id='llava-scan-button'" in response.text
    assert 'data-scanner-llava-fallback-seconds="5"' in response.text
    assert 'data-scanner-llava-timeout-seconds="45"' in response.text
    assert 'data-dashboard-polling-interval-seconds="5"' in response.text


def test_dashboard_scanner_llava_endpoint(client, monkeypatch):
    def fake_detect_product_from_image(self, image_base64, *, timeout_seconds=90):
        assert image_base64 == "abc123"
        assert timeout_seconds == 45
        return {
            "product_name": "Apfelsaft",
            "brand": "Biohof",
            "hint": "1L Karton",
        }

    monkeypatch.setattr(
        routes.IngredientDetector,
        "detect_product_from_image",
        fake_detect_product_from_image,
    )

    response = client.post(
        "/api/dashboard/scanner/llava",
        headers={"Authorization": "Bearer test-api-key"},
        json={"image_base64": "abc123"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "product_name": "Apfelsaft",
        "brand": "Biohof",
        "hint": "1L Karton",
        "source": "ollama_llava",
    }


def test_dashboard_scanner_llava_endpoint_returns_429_when_busy(client, monkeypatch):
    monkeypatch.setattr(
        routes, "_acquire_llava_request_slot", lambda timeout_seconds: False
    )

    response = client.post(
        "/api/dashboard/scanner/llava",
        headers={"Authorization": "Bearer test-api-key"},
        json={"image_base64": "abc123"},
    )

    assert response.status_code == 429


def test_dashboard_scanner_create_product_uses_scanner_metadata(client, monkeypatch):
    calls = {}

    class FakeGrocyClient:
        def __init__(self, settings):
            self.settings = settings

        def get_locations(self):
            return [{"id": 7, "name": "Vorrat"}]

        def get_quantity_units(self):
            return {4: "Stück"}

        def create_product(self, payload):
            calls["created"] = payload
            return 321

        def update_product_nutrition(
            self,
            product_id,
            calories=None,
            carbs=None,
            fat=None,
            protein=None,
            sugar=None,
        ):
            calls["nutrition"] = {
                "product_id": product_id,
                "calories": calories,
                "carbs": carbs,
                "fat": fat,
                "protein": protein,
                "sugar": sugar,
            }

        def get_product_default_best_before_days(self, product_id):
            calls["default_days_lookup"] = product_id
            return None

        def set_product_default_best_before_days(self, product_id, days):
            calls["default_days_set"] = (product_id, days)

        def set_product_barcode(self, product_id, barcode):
            calls["barcode"] = (product_id, barcode)

        def add_product_to_shopping_list(self, product_id, amount, best_before_date=""):
            calls["added"] = (product_id, amount, best_before_date)

    monkeypatch.setattr(routes, "GrocyClient", FakeGrocyClient)

    response = client.post(
        "/api/dashboard/scanner/create-product",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "product_name": "Haferdrink",
            "source": "OpenFoodFacts",
            "barcode": "4008400408400",
            "brand": "Oatly",
            "quantity": "1 l",
            "ingredients_text": "Wasser, Hafer",
            "nutrition_grade": "B",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "action": "created_and_added",
        "message": "Haferdrink wurde neu angelegt und zur Einkaufsliste hinzugefügt.",
        "product_id": 321,
        "variants": [],
    }
    assert calls["created"] == {
        "name": "Haferdrink",
        "description": (
            "Marke: Oatly\n"
            "Menge: 1 l\n"
            "Nutrition-Grade: B\n"
            "Zutaten: Wasser, Hafer\n"
            "Quelle: OpenFoodFacts"
        ),
        "location_id": 7,
        "qu_id_purchase": 4,
        "qu_id_stock": 4,
        "default_best_before_days": 0,
    }
    assert calls["nutrition"] == {
        "product_id": 321,
        "calories": 0,
        "carbs": 0,
        "fat": 0,
        "protein": 0,
        "sugar": 0,
    }
    assert calls["default_days_lookup"] == 321
    assert calls["default_days_set"] == (321, 0)
    assert calls["barcode"] == (321, "4008400408400")
    assert calls["added"] == (321, 1, "")


def test_recipe_suggestions_strip_html_from_grocy_and_ai_fields(client, monkeypatch):
    def fake_get_stock_products(self):
        return [
            {"id": 1, "name": "Tomate", "location_name": "Kühlschrank", "amount": "2"}
        ]

    def fake_get_recipes(self):
        return [
            {
                "id": 10,
                "name": "<b>Tomaten Pasta</b>",
                "description": "<p>Pasta<br>kochen</p>",
            }
        ]

    class FakeDetector:
        def __init__(self, settings):
            self.settings = settings

        def generate_recipe_suggestions(
            self, selected_products, existing_recipe_titles
        ):
            return [
                {
                    "title": "<h2>Tomaten-Suppe</h2>",
                    "reason": "<p>Tomate<br>ist vorhanden</p>",
                    "preparation": "<div>Tomaten schneiden</div>",
                    "ingredients": ["<li>2 Tomaten</li>"],
                }
            ]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )
    monkeypatch.setattr(routes.GrocyClient, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(
        routes.GrocyClient, "get_missing_recipe_products", lambda self, recipe_id: []
    )
    monkeypatch.setattr(
        routes.GrocyClient,
        "get_recipe_ingredients",
        lambda self, recipe_id: ["180 g Tomate"],
    )
    monkeypatch.setattr(routes, "IngredientDetector", FakeDetector)

    response = client.post(
        "/api/dashboard/recipe-suggestions",
        headers={"Authorization": "Bearer test-api-key"},
        json={"product_ids": [1]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["grocy_recipes"][0]["title"] == "Tomaten Pasta"
    assert payload["grocy_recipes"][0]["preparation"] == "Pasta\nkochen"
    assert payload["ai_recipes"][0]["title"] == "Tomaten-Suppe"
    assert payload["ai_recipes"][0]["reason"] == "Tomate\nist vorhanden"
    assert payload["ai_recipes"][0]["preparation"] == "Tomaten schneiden"
    assert payload["ai_recipes"][0]["ingredients"] == ["2 Tomaten"]


def test_dashboard_has_storage_tab_before_notifications(client):
    response = client.get("/")

    assert response.status_code == 200
    storage_pos = response.text.index("id='tab-button-storage'")
    notify_pos = response.text.index("id='tab-button-notifications'")

    assert storage_pos < notify_pos
    assert 'switchTab("storage")' in response.text
    assert "<h2>Lager</h2>" in response.text
    assert "id='storage-include-all-products'" in response.text


def test_dashboard_static_contains_storage_actions(client):
    response = client.get("/dashboard-static/dashboard.js")

    assert response.status_code == 200
    assert "function loadStorageProducts()" in response.text
    assert "function consumeStorageProduct(stockId)" in response.text
    assert "function openStorageEditModal(stockId)" in response.text
    assert "function saveStorageEditModal()" in response.text
    assert "function deleteStorageEditPicture()" in response.text


def test_dashboard_stock_products_include_stock_id(client, monkeypatch):
    def fake_get_stock_products(self, location_ids=None):
        return [
            {
                "id": 10,
                "stock_id": 99,
                "name": "Milch",
                "picture_url": "milk.png",
                "location_id": 1,
                "location_name": "Küche",
                "amount": "2",
                "best_before_date": "2026-01-01",
                "calories": "120",
                "carbs": "4.5",
                "fat": "3.2",
                "protein": "8",
                "sugar": "4",
            }
        ]

    monkeypatch.setattr(
        routes.GrocyClient, "get_stock_products", fake_get_stock_products
    )

    response = client.get(
        "/api/dashboard/stock-products",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()[0]["stock_id"] == 99
    assert response.json()[0]["calories"] == "120"
    assert response.json()[0]["carbs"] == "4.5"
    assert response.json()[0]["fat"] == "3.2"
    assert response.json()[0]["protein"] == "8"
    assert response.json()[0]["sugar"] == "4"
    assert "/api/dashboard/product-picture?src=" in response.json()[0]["picture_url"]
    assert (
        "homeassistant.local%3A9192%2Fapi%2Ffiles%2Fproductpictures%2F"
        in response.json()[0]["picture_url"]
    )


def test_dashboard_product_nutrition_reads_userfields(client, monkeypatch):
    def fake_get_product_nutrition(self, product_id):
        assert product_id == 10
        return {
            "calories": "120",
            "carbs": "4.5",
            "fat": "3.2",
            "protein": "8",
            "sugar": "4",
        }

    monkeypatch.setattr(
        routes.GrocyClient,
        "get_product_nutrition",
        fake_get_product_nutrition,
    )

    response = client.get(
        "/api/dashboard/products/10/nutrition",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "calories": "120",
        "carbs": "4.5",
        "fat": "3.2",
        "protein": "8",
        "sugar": "4",
    }


def test_dashboard_can_delete_product_picture(client, monkeypatch):
    called = {}

    def fake_clear_product_picture(self, product_id):
        called["product_id"] = product_id

    monkeypatch.setattr(
        routes.GrocyClient, "clear_product_picture", fake_clear_product_picture
    )

    response = client.delete(
        "/api/dashboard/products/10/picture",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert called["product_id"] == 10


def test_dashboard_can_consume_stock_product(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"id": 99, "product_id": 10}]

    called = {}

    def fake_consume_stock_product(self, product_id, amount=1, stock_id=None):
        called["args"] = (product_id, amount, stock_id)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "consume_stock_product", fake_consume_stock_product
    )

    response = client.post(
        "/api/dashboard/stock-products/99/consume",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 1},
    )

    assert response.status_code == 200
    assert called["args"] == (10, 1, 99)


def test_dashboard_can_consume_stock_product_by_stock_id_field(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"stock_id": 99, "product_id": 10}]

    called = {}

    def fake_consume_stock_product(self, product_id, amount=1, stock_id=None):
        called["args"] = (product_id, amount, stock_id)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "consume_stock_product", fake_consume_stock_product
    )

    response = client.post(
        "/api/dashboard/stock-products/99/consume",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 1},
    )

    assert response.status_code == 200
    assert called["args"] == (10, 1, 99)


def test_dashboard_can_consume_stock_product_by_product_id_fallback(
    client, monkeypatch
):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"stock_id": 321, "product_id": 99}]

    called = {}

    def fake_consume_stock_product(self, product_id, amount=1, stock_id=None):
        called["args"] = (product_id, amount, stock_id)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "consume_stock_product", fake_consume_stock_product
    )

    response = client.post(
        "/api/dashboard/stock-products/99/consume",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 1},
    )

    assert response.status_code == 200
    assert called["args"] == (99, 1, 321)


def test_dashboard_consume_stock_product_prefers_product_id_hint(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [
            {"stock_id": 99, "product_id": 10},
            {"stock_id": 55, "product_id": 99},
        ]

    called = {}

    def fake_consume_stock_product(self, product_id, amount=1, stock_id=None):
        called["args"] = (product_id, amount, stock_id)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "consume_stock_product", fake_consume_stock_product
    )

    response = client.post(
        "/api/dashboard/stock-products/99/consume?product_id=99",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 1},
    )

    assert response.status_code == 200
    assert called["args"] == (99, 1, 55)


def test_dashboard_can_update_stock_product_by_product_id_fallback(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"id": 321, "product_id": 99}]

    called = {}

    def fake_set_product_inventory(self, product_id, amount, stock_id=None):
        called["args"] = (product_id, amount, stock_id)

    nutrition_called = {}

    def fake_update_product_nutrition(
        self,
        product_id,
        calories=None,
        carbs=None,
        fat=None,
        protein=None,
        sugar=None,
    ):
        nutrition_called["args"] = (product_id, calories, carbs, fat, protein, sugar)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "set_product_inventory", fake_set_product_inventory
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_nutrition", fake_update_product_nutrition
    )

    response = client.put(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "amount": 5,
            "best_before_date": "2026-02-01",
            "calories": 100,
            "carbs": 12,
            "fat": 1.5,
            "protein": 3,
            "sugar": 7,
        },
    )

    assert response.status_code == 200
    assert called["args"] == (99, 5, 321)
    assert nutrition_called["args"] == (99, 100, 12, 1.5, 3, 7)


def test_dashboard_uses_resolved_stock_id_for_absolute_update(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"id": 0, "product_id": 99, "location_id": 2}]

    called = {}

    def fake_resolve_stock_entry_id_for_product(self, product_id, location_id=None):
        called["resolve"] = (product_id, location_id)
        return 321

    def fake_set_product_inventory(self, product_id, amount, stock_id=None):
        called["inventory"] = (product_id, amount, stock_id)

    def fake_update_product_nutrition(
        self,
        product_id,
        calories=None,
        carbs=None,
        fat=None,
        protein=None,
        sugar=None,
    ):
        called["nutrition"] = (product_id, calories, carbs, fat, protein, sugar)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient,
        "resolve_stock_entry_id_for_product",
        fake_resolve_stock_entry_id_for_product,
    )
    monkeypatch.setattr(
        routes.GrocyClient, "set_product_inventory", fake_set_product_inventory
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_nutrition", fake_update_product_nutrition
    )

    response = client.put(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 1, "best_before_date": "2026-02-01"},
    )

    assert response.status_code == 200
    assert called["resolve"] == (99, 2)
    assert called["inventory"] == (99, 1, 321)
    assert called["nutrition"] == (99, None, None, None, None, None)


def test_dashboard_creates_stock_entry_when_stock_id_missing(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"id": 0, "product_id": 99}]

    add_called = {}

    def fake_add_product_to_stock(self, product_id, amount, best_before_date=""):
        add_called["args"] = (product_id, amount, best_before_date)

    nutrition_called = {}

    def fake_update_product_nutrition(
        self,
        product_id,
        calories=None,
        carbs=None,
        fat=None,
        protein=None,
        sugar=None,
    ):
        nutrition_called["args"] = (product_id, calories, carbs, fat, protein, sugar)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient,
        "resolve_stock_entry_id_for_product",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        routes.GrocyClient, "add_product_to_stock", fake_add_product_to_stock
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_nutrition", fake_update_product_nutrition
    )

    response = client.put(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 5, "best_before_date": "2026-02-01"},
    )

    assert response.status_code == 200
    assert add_called["args"] == (99, 5, "2026-02-01")
    assert nutrition_called["args"] == (99, None, None, None, None, None)


def test_dashboard_allows_zero_amount_when_stock_id_missing(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"id": 0, "product_id": 99}]

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient,
        "resolve_stock_entry_id_for_product",
        lambda *args, **kwargs: None,
    )

    called = {}

    def fake_set_product_inventory(self, product_id, amount, stock_id=None):
        called["inventory"] = (product_id, amount, stock_id)

    monkeypatch.setattr(
        routes.GrocyClient, "set_product_inventory", fake_set_product_inventory
    )

    response = client.put(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 0, "best_before_date": ""},
    )

    assert response.status_code == 200
    assert called["inventory"] == (99, 0, None)


def test_dashboard_can_delete_stock_product(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"id": 99, "product_id": 10}]

    called = {}

    def fake_delete_product(self, product_id):
        called["product_id"] = product_id

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(routes.GrocyClient, "delete_product", fake_delete_product)

    response = client.delete(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert called["product_id"] == 10


def test_dashboard_can_delete_stock_product_by_product_id_fallback(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"id": 321, "product_id": 99}]

    called = {}

    def fake_delete_product(self, product_id):
        called["product_id"] = product_id

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(routes.GrocyClient, "delete_product", fake_delete_product)

    response = client.delete(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert called["product_id"] == 99


def test_dashboard_delete_stock_product_prefers_product_id_hint(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [
            {"stock_id": 99, "product_id": 10},
            {"stock_id": 55, "product_id": 99},
        ]

    called = {}

    def fake_delete_product(self, product_id):
        called["product_id"] = product_id

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(routes.GrocyClient, "delete_product", fake_delete_product)

    response = client.delete(
        "/api/dashboard/stock-products/99?product_id=99",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert called["product_id"] == 99


def test_dashboard_can_update_stock_product(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"id": 99, "product_id": 10}]

    called = {}

    def fake_set_product_inventory(self, product_id, amount, stock_id=None):
        called["args"] = (product_id, amount, stock_id)

    nutrition_called = {}

    def fake_update_product_nutrition(
        self,
        product_id,
        calories=None,
        carbs=None,
        fat=None,
        protein=None,
        sugar=None,
    ):
        nutrition_called["args"] = (product_id, calories, carbs, fat, protein, sugar)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "set_product_inventory", fake_set_product_inventory
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_nutrition", fake_update_product_nutrition
    )

    response = client.put(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 5, "best_before_date": "2026-02-01"},
    )

    assert response.status_code == 200
    assert called["args"] == (10, 5, 99)
    assert nutrition_called["args"] == (10, None, None, None, None, None)


def test_dashboard_update_stock_product_prefers_product_id_hint(client, monkeypatch):
    def fake_get_stock_entries(self, location_ids=None):
        return [
            {"stock_id": 99, "product_id": 10, "location_id": 1},
            {"stock_id": 55, "product_id": 99, "location_id": 2},
        ]

    called = {}

    def fake_set_product_inventory(self, product_id, amount, stock_id=None):
        called["inventory"] = (product_id, amount, stock_id)

    def fake_update_product_nutrition(
        self,
        product_id,
        calories=None,
        carbs=None,
        fat=None,
        protein=None,
        sugar=None,
    ):
        called["nutrition"] = (product_id, calories, carbs, fat, protein, sugar)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "set_product_inventory", fake_set_product_inventory
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_nutrition", fake_update_product_nutrition
    )

    response = client.put(
        "/api/dashboard/stock-products/99?product_id=99",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 3, "best_before_date": ""},
    )

    assert response.status_code == 200
    assert called["inventory"] == (99, 3, 55)
    assert called["nutrition"] == (99, None, None, None, None, None)


def test_dashboard_update_stock_product_skips_inventory_when_amount_unchanged(
    client, monkeypatch
):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"stock_id": 99, "product_id": 10, "amount": "5"}]

    called = {"inventory": 0}

    def fake_set_product_inventory(self, product_id, amount, stock_id=None):
        called["inventory"] += 1

    def fake_update_product_nutrition(
        self,
        product_id,
        calories=None,
        carbs=None,
        fat=None,
        protein=None,
        sugar=None,
    ):
        called["nutrition"] = (product_id, calories, carbs, fat, protein, sugar)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "set_product_inventory", fake_set_product_inventory
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_nutrition", fake_update_product_nutrition
    )

    response = client.put(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 5, "best_before_date": "", "calories": 120},
    )

    assert response.status_code == 200
    assert called["inventory"] == 0
    assert called["nutrition"] == (10, 120, None, None, None, None)


def test_dashboard_update_stock_product_supports_out_of_stock_products(
    client, monkeypatch
):
    def fake_get_stock_entries(self, location_ids=None):
        return [{"stock_id": 11, "product_id": 10, "amount": "2"}]

    called = {}

    def fake_resolve_stock_entry_id_for_product(self, product_id, location_id=None):
        called["resolve"] = (product_id, location_id)
        return None

    def fake_set_product_inventory(self, product_id, amount, stock_id=None):
        called["inventory"] = (product_id, amount, stock_id)

    def fake_add_product_to_stock(self, product_id, amount, best_before_date=""):
        called["add"] = (product_id, amount, best_before_date)

    def fake_update_product_nutrition(
        self,
        product_id,
        calories=None,
        carbs=None,
        fat=None,
        protein=None,
        sugar=None,
    ):
        called["nutrition"] = (product_id, calories, carbs, fat, protein, sugar)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient,
        "resolve_stock_entry_id_for_product",
        fake_resolve_stock_entry_id_for_product,
    )
    monkeypatch.setattr(
        routes.GrocyClient, "set_product_inventory", fake_set_product_inventory
    )
    monkeypatch.setattr(
        routes.GrocyClient, "add_product_to_stock", fake_add_product_to_stock
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_nutrition", fake_update_product_nutrition
    )

    response = client.put(
        "/api/dashboard/stock-products/777?product_id=777",
        headers={"Authorization": "Bearer test-api-key"},
        json={"amount": 4, "best_before_date": ""},
    )

    assert response.status_code == 200
    assert called["resolve"] == (777, None)
    assert "inventory" not in called
    assert called["add"] == (777, 4, "")
    assert called["nutrition"] == (777, None, None, None, None, None)


def test_dashboard_update_stock_product_updates_location_and_best_before(
    client, monkeypatch
):
    def fake_get_stock_entries(self, location_ids=None):
        return [
            {
                "stock_id": 99,
                "product_id": 10,
                "amount": "5",
                "location_id": 2,
                "best_before_date": "2026-03-20",
            }
        ]

    called = {}

    def fake_update_product_location(self, product_id, location_id):
        called["product_location"] = (product_id, location_id)

    def fake_update_stock_entry(
        self, stock_id, amount, best_before_date="", location_id=None
    ):
        called["stock_update"] = (stock_id, amount, best_before_date, location_id)

    def fake_update_product_nutrition(
        self,
        product_id,
        calories=None,
        carbs=None,
        fat=None,
        protein=None,
        sugar=None,
    ):
        called["nutrition"] = (product_id, calories, carbs, fat, protein, sugar)

    monkeypatch.setattr(routes.GrocyClient, "get_stock_entries", fake_get_stock_entries)
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_location", fake_update_product_location
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_stock_entry", fake_update_stock_entry
    )
    monkeypatch.setattr(
        routes.GrocyClient, "update_product_nutrition", fake_update_product_nutrition
    )

    response = client.put(
        "/api/dashboard/stock-products/99",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "amount": 5,
            "best_before_date": "2026-03-25",
            "location_id": 7,
        },
    )

    assert response.status_code == 200
    assert called["product_location"] == (10, 7)
    assert called["stock_update"] == (99, 5, "2026-03-25", 7)
    assert called["nutrition"] == (10, None, None, None, None, None)
