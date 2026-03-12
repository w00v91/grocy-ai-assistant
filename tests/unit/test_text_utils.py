from grocy_ai_assistant.core.text_utils import html_to_plain_text


def test_html_to_plain_text_strips_tags_and_decodes_entities():
    assert html_to_plain_text("<p>Tomate &amp; Basilikum<br><b>frisch</b></p>") == (
        "Tomate & Basilikum\nfrisch"
    )


def test_html_to_plain_text_handles_plain_text_input():
    assert html_to_plain_text("  Nur Text  ") == "Nur Text"
