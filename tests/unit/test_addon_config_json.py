import json
from pathlib import Path

from grocy_ai_assistant.config import options_store


def test_addon_config_enables_ingress_on_service_port():
    config_path = (
        Path(__file__).resolve().parents[2] / "grocy_ai_assistant" / "config.json"
    )
    config = json.loads(config_path.read_text())

    assert config["ingress"] is True
    assert config["ingress_port"] == 8000


def test_addon_config_contains_global_notification_toggle():
    config_path = (
        Path(__file__).resolve().parents[2] / "grocy_ai_assistant" / "config.json"
    )
    config = json.loads(config_path.read_text())

    assert config["options"]["notification_global_enabled"] is True
    assert config["schema"]["notification_global_enabled"] == "bool"


def test_addon_config_contains_image_generation_options():
    config_path = (
        Path(__file__).resolve().parents[2] / "grocy_ai_assistant" / "config.json"
    )
    config = json.loads(config_path.read_text())

    assert config["options"]["image_generation_enabled"] is False
    assert config["schema"]["image_generation_enabled"] == "bool"
    assert config["schema"]["openai_api_key"] == "password"
    assert config["options"]["openai_image_model"] == "gpt-image-1"


def test_addon_config_contains_startup_batch_image_option():
    config_path = (
        Path(__file__).resolve().parents[2] / "grocy_ai_assistant" / "config.json"
    )
    config = json.loads(config_path.read_text())

    assert config["options"]["generate_missing_product_images_on_startup"] is False
    assert config["schema"]["generate_missing_product_images_on_startup"] == "bool"


def test_addon_config_enables_supervisor_and_homeassistant_api():
    config_path = (
        Path(__file__).resolve().parents[2] / "grocy_ai_assistant" / "config.json"
    )
    config = json.loads(config_path.read_text())

    assert config["homeassistant_api"] is True
    assert config["hassio_api"] is True


def test_addon_config_contains_initial_info_sync_option():
    config_path = (
        Path(__file__).resolve().parents[2] / "grocy_ai_assistant" / "config.json"
    )
    config = json.loads(config_path.read_text())

    assert config["options"]["initial_info_sync"] is False
    assert config["schema"]["initial_info_sync"] == "bool"


def test_repository_config_yaml_matches_config_json():
    repo_root = Path(__file__).resolve().parents[2]
    config_json = json.loads(
        (repo_root / "grocy_ai_assistant" / "config.json").read_text(encoding="utf-8")
    )
    config_yaml = options_store.parse_simple_yaml(
        (repo_root / "grocy_ai_assistant" / "config.yaml").read_text(encoding="utf-8")
    )

    assert config_yaml == config_json
