import json
from pathlib import Path


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
