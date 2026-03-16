from pathlib import Path
import logging

import requests

from grocy_ai_assistant.ai.ingredient_detector import IngredientDetector
from grocy_ai_assistant.config.settings import Settings


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_generate_recipe_suggestions_normalizes_preparation_fields(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": '[{"title":"Suppe","reason":"passt","details":"Gemüse kochen"}, {"title":"Salat","reason":"frisch","preparation":"Mischen"}]'
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.generate_recipe_suggestions(["Tomate"], ["Pasta"])

    assert result == [
        {
            "title": "Suppe",
            "reason": "passt",
            "preparation": "Gemüse kochen",
            "ingredients": [],
        },
        {
            "title": "Salat",
            "reason": "frisch",
            "preparation": "Mischen",
            "ingredients": [],
        },
    ]


def test_generate_recipe_suggestions_decodes_escaped_newlines(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": '[{"title":"Apfel, Butter Pfanne\\\\nSchnell","reason":"Resteverwertung\\\\nmit Bestand","preparation":"Schritt 1\\\\nSchritt 2"}]'
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.generate_recipe_suggestions(["Apfel", "Butter"], [])

    assert result == [
        {
            "title": "Apfel, Butter Pfanne\nSchnell",
            "reason": "Resteverwertung\nmit Bestand",
            "preparation": "Schritt 1\nSchritt 2",
            "ingredients": [],
        }
    ]


def test_generate_recipe_suggestions_extracts_embedded_recipe_sections(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": (
                    '[{"title":"Apfel Salat\\nLeichtes Rezept, das mit den vorhandenen Zutaten startet.'
                    "\\nZubereitung\\nApfel schneiden und mit Nüssen vermischen."
                    '\\n\\nFehlende Produkte\\nKeine fehlenden Produkte.","reason":"","preparation":""}]'
                )
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.generate_recipe_suggestions(["Apfel"], [])

    assert result == [
        {
            "title": "Apfel Salat",
            "reason": "Leichtes Rezept, das mit den vorhandenen Zutaten startet.",
            "preparation": "Apfel schneiden und mit Nüssen vermischen.",
            "ingredients": [],
        }
    ]


def test_generate_recipe_suggestions_accepts_single_object_payload(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": '{"title":"Apfel-Käse-Toast","reason":"passt","preparation":"Toast rösten"}'
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.generate_recipe_suggestions(["Apfel"], [])

    assert result == [
        {
            "title": "Apfel-Käse-Toast",
            "reason": "passt",
            "preparation": "Toast rösten",
            "ingredients": [],
        }
    ]


def test_generate_recipe_suggestions_normalizes_ingredients_list(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": '[{"title":"Curry","reason":"passt","preparation":"Kochen","ingredients":["2 Karotten","  ","1 Dose Kokosmilch"]}]'
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.generate_recipe_suggestions(["Karotte"], [])

    assert result == [
        {
            "title": "Curry",
            "reason": "passt",
            "preparation": "Kochen",
            "ingredients": ["2 Karotten", "1 Dose Kokosmilch"],
        }
    ]


def test_generate_recipe_suggestions_strips_html_from_fields(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": '[{"title":"<b>Curry</b>","reason":"<p>passt<br>gut</p>","preparation":"<div>Kochen</div>","ingredients":["<li>2 Karotten</li>"]}]'
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.generate_recipe_suggestions(["Karotte"], [])

    assert result == [
        {
            "title": "Curry",
            "reason": "passt\ngut",
            "preparation": "Kochen",
            "ingredients": ["2 Karotten"],
        }
    ]


def test_generate_recipe_suggestions_extracts_embedded_ingredients_sections(
    monkeypatch,
):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": (
                    '[{"title":"Gemüsepfanne\\nSchnell gemacht\\nZutaten\\n- 2 Karotten\\n- 1 Zucchini\\nZubereitung\\nAlles anbraten.","reason":"","preparation":""}]'
                )
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.generate_recipe_suggestions(["Karotte", "Zucchini"], [])

    assert result == [
        {
            "title": "Gemüsepfanne",
            "reason": "Schnell gemacht",
            "preparation": "Alles anbraten.",
            "ingredients": ["2 Karotten", "1 Zucchini"],
        }
    ]


def test_generate_recipe_suggestions_logs_raw_ai_response_in_debug_mode(
    monkeypatch, caplog
):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {"response": '[{"title":"Suppe","reason":"passt","preparation":"Kochen"}]'}
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            debug_mode=True,
        )
    )

    with caplog.at_level(logging.INFO):
        detector.generate_recipe_suggestions(["Tomate"], [])

    assert "KI-Antwort generate_recipe_suggestions" in caplog.text


def test_detect_product_from_image_uses_configurable_min_confidence(monkeypatch):
    captured_payload = {}

    def fake_post(*args, **kwargs):
        captured_payload.update(kwargs.get("json") or {})
        return FakeResponse(
            {"response": '{"product_name":"Milch","brand":"Bio","hint":"1L"}'}
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            scanner_llava_min_confidence=82,
        )
    )

    result = detector.detect_product_from_image("img")

    assert "mindestens 82 prozent sicher" in captured_payload["prompt"]
    assert result == {"product_name": "Milch", "brand": "Bio", "hint": "1L"}


def test_detect_product_from_image_returns_empty_on_null_response(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse({"response": "null"})

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.detect_product_from_image("img")

    assert result == {"product_name": "", "brand": "", "hint": ""}


def test_generate_product_image_uses_openai_images_api(monkeypatch, tmp_path):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json

        class FakeImageResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": [{"b64_json": "aGVsbG8="}]}

        return FakeImageResponse()

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.Path",
        lambda value: tmp_path / str(value).strip("/"),
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            image_generation_enabled=True,
            openai_api_key="sk-test",
            openai_image_model="gpt-image-1",
        )
    )

    result = detector.generate_product_image("Hafer Milch")

    assert captured["url"] == "https://api.openai.com/v1/images/generations"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["json"]["model"] == "gpt-image-1"
    assert 'Erstelle ein produktbild für "Hafer Milch"' in captured["json"]["prompt"]
    assert Path(result).exists()


def test_generate_product_image_falls_back_to_dalle_on_403(monkeypatch, tmp_path):
    captured_models = []

    class FakeForbiddenResponse:
        status_code = 403

        def raise_for_status(self):
            raise requests.HTTPError("forbidden", response=self)

    class FakeSuccessResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"b64_json": "aGVsbG8="}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured_models.append(json["model"])
        if json["model"] == "gpt-image-1":
            return FakeForbiddenResponse()
        return FakeSuccessResponse()

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.Path",
        lambda value: tmp_path / str(value).strip("/"),
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            image_generation_enabled=True,
            openai_api_key="sk-test",
            openai_image_model="gpt-image-1",
        )
    )

    result = detector.generate_product_image("Zucchini")

    assert captured_models == ["gpt-image-1", "dall-e-3"]
    assert Path(result).exists()


def test_generate_product_image_downloads_from_url_when_b64_missing(
    monkeypatch, tmp_path
):
    class FakeImageApiResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"url": "https://example.invalid/image.png"}]}

    class FakeDownloadResponse:
        def __init__(self):
            self.content = b"png-bytes"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post",
        lambda *args, **kwargs: FakeImageApiResponse(),
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.get",
        lambda *args, **kwargs: FakeDownloadResponse(),
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.Path",
        lambda value: tmp_path / str(value).strip("/"),
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            image_generation_enabled=True,
            openai_api_key="sk-test",
            openai_image_model="gpt-image-1",
        )
    )

    result = detector.generate_product_image("Tomate")

    assert Path(result).read_bytes() == b"png-bytes"


def test_analyze_product_name_returns_extended_nutrition_values(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": (
                    '{"name":"Haferflocken","description":"Vollkorn",'
                    '"location_id":2,"qu_id_purchase":1,"qu_id_stock":3,'
                    '"calories":372,"carbohydrates":"58,7","fat":"7.0",'
                    '"protein":"13,5","sugar":"0,8"}'
                )
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.analyze_product_name("Haferflocken")

    assert result["calories"] == 372
    assert result["carbohydrates"] == 58.7
    assert result["fat"] == 7
    assert result["protein"] == 13.5
    assert result["sugar"] == 0.8
    assert result["default_best_before_days"] == 0


def test_analyze_product_name_maps_carbs_alias(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": (
                    '{"name":"Muesli","description":"",'
                    '"location_id":"2","qu_id_purchase":"1","qu_id_stock":"1",'
                    '"calories":"410","carbs":"64"}'
                )
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.analyze_product_name("Muesli")

    assert result["carbohydrates"] == 64
    assert result["fat"] == 0
    assert result["protein"] == 0
    assert result["sugar"] == 0


def test_analyze_product_name_maps_default_best_before_days(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": (
                    '{"name":"Joghurt","description":"","location_id":1,'
                    '"qu_id_purchase":1,"qu_id_stock":1,"calories":60,'
                    '"default_best_before_days":"7"}'
                )
            }
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.ai.ingredient_detector.requests.post", fake_post
    )

    detector = IngredientDetector(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = detector.analyze_product_name("Joghurt")

    assert result["default_best_before_days"] == 7
