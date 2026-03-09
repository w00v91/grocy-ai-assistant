from grocy_ai_assistant.core.engine import process_ingredient


def test_process_ingredient_returns_expected_payload():
    result = process_ingredient("Tomate")

    assert result == {"status": "processed", "ingredient": "Tomate"}
