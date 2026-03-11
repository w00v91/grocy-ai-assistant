from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable when tests are run from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import grocy_ai_assistant.api.main as api_main
from grocy_ai_assistant.api.main import app
from grocy_ai_assistant.api.routes import get_settings
from grocy_ai_assistant.config.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        api_key="test-api-key",
        addon_version="2026.03.0",
        required_integration_version="1.2.10",
        grocy_api_key="test-grocy-key",
    )


@pytest.fixture
def client(test_settings: Settings, monkeypatch):
    monkeypatch.setattr(
        api_main, "prefetch_initial_recipe_suggestions", lambda settings: None
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
