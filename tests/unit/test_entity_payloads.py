import importlib.util
from datetime import date
from pathlib import Path


def _load_entity_payloads_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "grocy_ai_assistant"
        / "custom_components"
        / "grocy_ai_assistant"
        / "entity_payloads.py"
    )
    spec = importlib.util.spec_from_file_location("entity_payloads", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


entity_payloads = _load_entity_payloads_module()


build_analysis_status_payload = entity_payloads.build_analysis_status_payload
build_barcode_status_payload = entity_payloads.build_barcode_status_payload
build_error_status_payload = entity_payloads.build_error_status_payload
build_expiring_stock_summary = entity_payloads.build_expiring_stock_summary
build_llava_status_payload = entity_payloads.build_llava_status_payload
build_recipe_summary = entity_payloads.build_recipe_summary
build_shopping_list_summary = entity_payloads.build_shopping_list_summary
build_stock_summary = entity_payloads.build_stock_summary


def test_build_shopping_list_summary_returns_count_and_attributes():
    count, attributes = build_shopping_list_summary(
        [
            {
                "id": 1,
                "product_name": "Milch",
                "location_name": "Küche",
                "best_before_date": "2026-03-22",
            },
            {
                "id": 2,
                "product_name": "Apfel",
                "location_name": "Speisekammer",
                "best_before_date": "",
            },
        ]
    )

    assert count == 2
    assert attributes["locations"] == ["Küche", "Speisekammer"]
    assert attributes["next_best_before_date"] == "2026-03-22"
    assert attributes["items"][0]["product_name"] == "Milch"
    assert attributes["updated_at"].endswith("Z")


def test_build_stock_summary_returns_count_and_locations():
    count, attributes = build_stock_summary(
        [
            {"id": 10, "name": "Pasta", "location_name": "Vorrat"},
            {"id": 11, "name": "Reis", "location_name": "Vorrat"},
        ]
    )

    assert count == 2
    assert attributes["locations"] == ["Vorrat"]
    assert [product["name"] for product in attributes["products"]] == ["Pasta", "Reis"]


def test_build_expiring_stock_summary_filters_by_date_window():
    count, attributes = build_expiring_stock_summary(
        [
            {"id": 1, "name": "Joghurt", "best_before_date": "2026-03-20"},
            {"id": 2, "name": "Nudeln", "best_before_date": "2026-03-27"},
            {"id": 3, "name": "Reis", "best_before_date": ""},
        ],
        expiring_within_days=3,
        today=date(2026, 3, 19),
    )

    assert count == 1
    assert attributes["expiring_within_days"] == 3
    assert attributes["next_best_before_date"] == "2026-03-20"
    assert attributes["products"][0]["name"] == "Joghurt"
    assert attributes["products"][0]["days_until_best_before"] == 1


def test_build_recipe_summary_prefers_first_grocy_recipe_as_top_recipe():
    state, attributes = build_recipe_summary(
        {
            "selected_products": ["Tomate"],
            "grocy_recipes": [
                {"title": "Tomaten Pasta", "source": "grocy"},
            ],
            "ai_recipes": [
                {"title": "Tomatensuppe", "source": "ai"},
            ],
        },
        soon_expiring_only=True,
        expiring_within_days=5,
    )

    assert state == "Tomaten Pasta"
    assert attributes["soon_expiring_only"] is True
    assert attributes["expiring_within_days"] == 5
    assert attributes["top_recipe"]["source"] == "grocy"
    assert attributes["recipes_count"] == 2


def test_build_recipe_summary_filters_to_single_ai_recipe_for_ai_sensor():
    state, attributes = build_recipe_summary(
        {
            "selected_products": ["Tomate"],
            "grocy_recipes": [
                {"title": "Tomaten Pasta", "source": "grocy"},
            ],
            "ai_recipes": [
                {"title": "Tomatensuppe", "source": "ai"},
                {"title": "Tomaten-Curry", "source": "ai"},
            ],
        },
        soon_expiring_only=False,
        expiring_within_days=3,
        source="ai",
    )

    assert state == "Tomatensuppe"
    assert attributes["source"] == "ai"
    assert attributes["top_recipe"]["source"] == "ai"
    assert attributes["grocy_recipes"] == []
    assert attributes["ai_recipes"] == [{"title": "Tomatensuppe", "source": "ai"}]
    assert attributes["recipes_count"] == 1


def test_build_analysis_status_payload_contains_last_result_attributes():
    state, attributes = build_analysis_status_payload(
        query="Milch",
        payload={
            "_http_status": 200,
            "success": True,
            "action": "add_to_shopping_list",
            "message": "Hinzugefügt",
            "product_id": 42,
            "variants": [{"id": 1, "name": "Milch 1L"}],
        },
        duration_ms=123.45,
    )

    assert state == "success"
    assert attributes["query"] == "Milch"
    assert attributes["action"] == "add_to_shopping_list"
    assert attributes["product_id"] == 42
    assert attributes["variants"][0]["name"] == "Milch 1L"
    assert attributes["duration_ms"] == 123.5


def test_build_barcode_status_payload_maps_found_result_fields():
    state, attributes = build_barcode_status_payload(
        barcode="4008400402222",
        payload={
            "_http_status": 200,
            "found": True,
            "product_name": "Müsli",
            "brand": "Beispiel",
            "quantity": "500 g",
            "ingredients_text": "Haferflocken",
            "nutrition_grade": "A",
            "source": "OpenFoodFacts",
        },
        duration_ms=50,
    )

    assert state == "match"
    assert attributes["barcode"] == "4008400402222"
    assert attributes["product_name"] == "Müsli"
    assert attributes["nutrition_grade"] == "A"
    assert attributes["duration_ms"] == 50.0


def test_build_llava_status_payload_maps_successful_scan_result():
    state, attributes = build_llava_status_payload(
        payload={
            "_http_status": 200,
            "success": True,
            "product_name": "Cornflakes",
            "brand": "ACME",
            "hint": "Gelbe Packung",
            "source": "ollama_llava",
        },
        duration_ms=87,
    )

    assert state == "success"
    assert attributes["product_name"] == "Cornflakes"
    assert attributes["brand"] == "ACME"
    assert attributes["hint"] == "Gelbe Packung"
    assert attributes["source"] == "ollama_llava"


def test_build_error_status_payload_marks_state_as_error():
    state, attributes = build_error_status_payload(
        source="barcode_lookup",
        error="Timeout",
        extra={"barcode": "123"},
    )

    assert state == "error"
    assert attributes["source"] == "barcode_lookup"
    assert attributes["error"] == "Timeout"
    assert attributes["barcode"] == "123"
