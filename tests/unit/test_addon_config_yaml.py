from pathlib import Path

from grocy_ai_assistant.config import options_store


CONFIG_PATH = Path(__file__).resolve().parents[2] / "grocy_ai_assistant" / "config.yaml"


def _load_config() -> dict:
    return options_store.parse_simple_yaml(CONFIG_PATH.read_text(encoding="utf-8"))


def test_addon_config_yaml_enables_ingress_on_service_port():
    config = _load_config()

    assert config["ingress"] is True
    assert config["ingress_port"] == 8000


def test_addon_config_yaml_contains_global_notification_toggle():
    config = _load_config()

    assert config["options"]["notification_global_enabled"] is True
    assert config["schema"]["notification_global_enabled"] == "bool"


def test_addon_config_yaml_contains_grouped_image_generation_options():
    config = _load_config()

    assert config["options"]["cloud_ai"]["image_generation_enabled"] is False
    assert config["schema"]["cloud_ai"]["image_generation_enabled"] == "bool"
    assert config["schema"]["cloud_ai"]["openai_api_key"] == "password"
    assert config["options"]["cloud_ai"]["openai_image_model"] == "gpt-image-1"


def test_addon_config_yaml_contains_grouped_startup_batch_image_option():
    config = _load_config()

    assert (
        config["options"]["cloud_ai"]["generate_missing_product_images_on_startup"]
        is False
    )
    assert (
        config["schema"]["cloud_ai"]["generate_missing_product_images_on_startup"]
        == "bool"
    )


def test_addon_config_yaml_enables_supervisor_and_homeassistant_api():
    config = _load_config()

    assert config["homeassistant_api"] is True
    assert config["hassio_api"] is True


def test_addon_config_yaml_contains_grouped_initial_info_sync_option():
    config = _load_config()

    assert config["options"]["ollama"]["initial_info_sync"] is False
    assert config["schema"]["ollama"]["initial_info_sync"] == "bool"


def test_repository_config_yaml_contains_expected_grouped_defaults():
    config = _load_config()

    assert config["version"] == "7.4.40"
    assert config["options"]["grocy"]["grocy_api_key"] == "DEIN_GROCY_KEY"
    assert config["schema"]["grocy"]["grocy_api_key"] == "str"
    assert config["options"]["debug_mode"] is False
    assert config["schema"]["debug_mode"] == "bool"


def test_addon_apparmor_profile_exists_and_matches_slug():
    repo_root = Path(__file__).resolve().parents[2]
    apparmor_path = repo_root / "grocy_ai_assistant" / "apparmor.txt"

    content = apparmor_path.read_text(encoding="utf-8")

    assert apparmor_path.exists()
    assert "profile grocy_ai_assistant" in content
    assert "/app/** rix," in content
    assert "/data/** rwk," in content
    assert "/config/** rwk," in content
    assert "network," in content
