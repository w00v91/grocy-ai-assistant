import json
from pathlib import Path


def test_addon_config_enables_ingress_on_service_port():
    config_path = (
        Path(__file__).resolve().parents[2] / "grocy_ai_assistant" / "config.json"
    )
    config = json.loads(config_path.read_text())

    assert config["ingress"] is True
    assert config["ingress_port"] == 8000
