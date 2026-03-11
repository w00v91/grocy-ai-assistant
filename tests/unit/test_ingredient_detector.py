import logging

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
        {"title": "Suppe", "reason": "passt", "preparation": "Gemüse kochen"},
        {"title": "Salat", "reason": "frisch", "preparation": "Mischen"},
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
        }
    ]


def test_generate_recipe_suggestions_extracts_embedded_recipe_sections(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": (
                    '[{"title":"Apfel Salat\\nLeichtes Rezept, das mit den vorhandenen Zutaten startet.'
                    '\\nZubereitung\\nApfel schneiden und mit Nüssen vermischen.'
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
        }
    ]


def test_generate_recipe_suggestions_logs_raw_ai_response_in_debug_mode(monkeypatch, caplog):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": '[{"title":"Suppe","reason":"passt","preparation":"Kochen"}]'
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
            debug_mode=True,
        )
    )

    with caplog.at_level(logging.INFO):
        detector.generate_recipe_suggestions(["Tomate"], [])

    assert (
        "KI-Antwort generate_recipe_suggestions" in caplog.text
    )
