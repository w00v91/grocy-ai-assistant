import pytest
from fastapi.testclient import TestClient

from grocy_ai_assistant.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
