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
        'api_key: DEIN_KI_KEY\n'
        'grocy_base_url: http://homeassistant.local:9192/api\n'
        'scanner_llava_timeout_seconds: 45\n'
        'notification_global_enabled: true\n'
        'image_generation_enabled: false\n'
    )
    assert options_store.parse_simple_yaml(dumped) == payload


def test_load_addon_options_prefers_yaml_then_repository_config_yaml(tmp_path, monkeypatch):
    yaml_path = tmp_path / "options.yaml"
    repository_config_path = tmp_path / "config.yaml"

    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", yaml_path)
    monkeypatch.setattr(
        options_store, "REPOSITORY_CONFIG_YAML_PATH", repository_config_path
    )

    repository_config_path.write_text(
        """name: Grocy AI Assistant
options:
  api_key: repo-default
  grocy:
    grocy_api_key: repo-grocy
  cloud_ai:
    image_generation_enabled: true
""",
        encoding="utf-8",
    )
    assert options_store.load_addon_options() == {
        "api_key": "repo-default",
        "grocy_api_key": "repo-grocy",
        "image_generation_enabled": True,
    }

    yaml_path.write_text(
        """options:
  api_key: yaml-wins
  grocy:
    grocy_api_key: yaml-grocy
  scanner:
    scanner_llava_timeout_seconds: 45
""",
        encoding="utf-8",
    )
    assert options_store.load_addon_options() == {
        "api_key": "yaml-wins",
        "grocy_api_key": "yaml-grocy",
        "scanner_llava_timeout_seconds": 45,
    }


def test_save_addon_options_writes_grouped_yaml_layout(tmp_path, monkeypatch):
    yaml_path = tmp_path / "options.yaml"
    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", yaml_path)

    options_store.save_addon_options(
        {
            "api_key": "yaml-wins",
            "notification_global_enabled": True,
            "grocy_api_key": "yaml-grocy",
            "grocy_base_url": "http://grocy.local/api",
            "initial_info_sync": False,
            "scanner_llava_timeout_seconds": 45,
            "image_generation_enabled": True,
            "generate_missing_product_images_on_startup": False,
        }
    )

    assert options_store.parse_simple_yaml(yaml_path.read_text(encoding="utf-8")) == {
        "api_key": "yaml-wins",
        "notification_global_enabled": True,
        "grocy": {
            "grocy_api_key": "yaml-grocy",
            "grocy_base_url": "http://grocy.local/api",
        },
        "ollama": {"initial_info_sync": False},
        "scanner": {"scanner_llava_timeout_seconds": 45},
        "cloud_ai": {
            "image_generation_enabled": True,
            "generate_missing_product_images_on_startup": False,
        },
    }



def test_save_addon_options_preserves_wrapped_options_layout(tmp_path, monkeypatch):
    yaml_path = tmp_path / "options.yaml"
    yaml_path.write_text(
        """options:
  grocy:
    grocy_api_key: old-key
metadata:
  source: supervisor
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", yaml_path)

    options_store.save_addon_options(
        {
            "grocy_api_key": "new-key",
            "grocy_base_url": "http://grocy.local/api",
        }
    )

    assert options_store.parse_simple_yaml(yaml_path.read_text(encoding="utf-8")) == {
        "options": {
            "grocy": {
                "grocy_api_key": "new-key",
                "grocy_base_url": "http://grocy.local/api",
            }
        },
        "metadata": {"source": "supervisor"},
    }


def test_load_addon_options_reads_mapped_values_from_deeply_nested_yaml_layout(
    tmp_path, monkeypatch
):
    yaml_path = tmp_path / "options.yaml"

    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", yaml_path)
    monkeypatch.setattr(
        options_store, "LEGACY_ADDON_OPTIONS_JSON_PATH", tmp_path / "options.json"
    )
    monkeypatch.setattr(
        options_store, "REPOSITORY_CONFIG_YAML_PATH", tmp_path / "config.yaml"
    )

    yaml_path.write_text(
        """options:
  profile:
    grocy:
      grocy_api_key: nested-grocy-key
      grocy_base_url: http://grocy.local/api
    cloud_ai:
      openai_api_key: nested-openai-key
  scanner:
    scanner_llava_timeout_seconds: 60
  api_key: top-level-key
  metadata:
    source: supervisor
""",
        encoding="utf-8",
    )

    assert options_store.load_addon_options() == {
        "api_key": "top-level-key",
        "grocy_api_key": "nested-grocy-key",
        "grocy_base_url": "http://grocy.local/api",
        "scanner_llava_timeout_seconds": 60,
        "openai_api_key": "nested-openai-key",
        "profile": {
            "grocy": {
                "grocy_api_key": "nested-grocy-key",
                "grocy_base_url": "http://grocy.local/api",
            },
            "cloud_ai": {"openai_api_key": "nested-openai-key"},
        },
        "metadata": {"source": "supervisor"},
    }
