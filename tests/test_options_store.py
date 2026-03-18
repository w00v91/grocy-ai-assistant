import json

from grocy_ai_assistant.config import options_store


def test_parse_and_dump_simple_yaml_roundtrip():
    payload = {
        "api_key": "DEIN_KI_KEY",
        "grocy_base_url": "http://homeassistant.local:9192/api",
        "scanner_llava_timeout_seconds": 45,
        "notification_global_enabled": True,
        "image_generation_enabled": False,
    }

    dumped = options_store.dump_simple_yaml(payload)

    assert dumped == (
        'api_key: "DEIN_KI_KEY"\n'
        'grocy_base_url: "http://homeassistant.local:9192/api"\n'
        "scanner_llava_timeout_seconds: 45\n"
        "notification_global_enabled: true\n"
        "image_generation_enabled: false\n"
    )
    assert options_store.parse_simple_yaml(dumped) == payload


def test_load_addon_options_prefers_yaml_then_legacy_json_then_repository_yaml(tmp_path, monkeypatch):
    yaml_path = tmp_path / "options.yaml"
    json_path = tmp_path / "options.json"
    repository_yaml_path = tmp_path / "repository-options.yaml"

    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", yaml_path)
    monkeypatch.setattr(options_store, "LEGACY_ADDON_OPTIONS_JSON_PATH", json_path)
    monkeypatch.setattr(options_store, "REPOSITORY_OPTIONS_YAML_PATH", repository_yaml_path)

    repository_yaml_path.write_text('api_key: "repo-default"\n', encoding="utf-8")
    assert options_store.load_addon_options() == {"api_key": "repo-default"}

    json_path.write_text(json.dumps({"api_key": "legacy-json"}), encoding="utf-8")
    assert options_store.load_addon_options() == {"api_key": "legacy-json"}

    yaml_path.write_text('api_key: "yaml-wins"\n', encoding="utf-8")
    assert options_store.load_addon_options() == {"api_key": "yaml-wins"}
