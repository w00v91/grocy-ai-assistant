from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from grocy_ai_assistant.api.main import app
from grocy_ai_assistant.api.routes import get_settings
from grocy_ai_assistant.config.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        api_key="test-api-key",
        addon_version="2026.03.0",
        required_integration_version="1.2.3",
    )


@pytest.fixture
def client(test_settings: Settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
