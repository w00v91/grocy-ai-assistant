import asyncio
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable when tests are run from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import grocy_ai_assistant.api.main as api_main
import grocy_ai_assistant.api.routes as api_routes
from grocy_ai_assistant.api.main import app
from grocy_ai_assistant.api.routes import get_settings
from grocy_ai_assistant.config.settings import Settings


@pytest.fixture(autouse=True)
def restore_stubbed_modules():
    tracked_names = {
        name: sys.modules.get(name)
        for name in list(sys.modules)
        if name == "homeassistant"
        or name.startswith("homeassistant.")
        or name == "grocy_ai_assistant.custom_components.grocy_ai_assistant"
        or name.startswith("grocy_ai_assistant.custom_components.grocy_ai_assistant.")
    }
    try:
        yield
    finally:
        current_names = list(sys.modules)
        for name in current_names:
            if name in tracked_names:
                original = tracked_names[name]
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original
            elif (
                name == "homeassistant"
                or name.startswith("homeassistant.")
                or name == "grocy_ai_assistant.custom_components.grocy_ai_assistant"
                or name.startswith(
                    "grocy_ai_assistant.custom_components.grocy_ai_assistant."
                )
            ):
                sys.modules.pop(name, None)


@pytest.fixture(autouse=True)
def enable_event_loop_debug():
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    previous_loop = None
    try:
        previous_loop = asyncio.get_event_loop()
    except RuntimeError:
        previous_loop = None
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        asyncio.set_event_loop(previous_loop)
        loop.close()


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
    class _FakeLocationCache:
        def __init__(self, settings):
            self.settings = settings

        def start(self):
            return None

        def stop(self):
            return None

        def get_locations(self):
            return []

        def refresh_locations(self):
            return 0

    class _FakeProductImageCache:
        def __init__(self, settings):
            self.settings = settings

        def start(self):
            return None

        def stop(self):
            return None

        def get_cached_image(self, *args, **kwargs):
            return None

        def refresh_all_product_images(self):
            return 0

    class _EmptyResponse:
        status_code = 200
        text = "[]"

        @staticmethod
        def json():
            return []

    monkeypatch.setattr(
        api_main, "prefetch_initial_recipe_suggestions", lambda settings: None
    )
    monkeypatch.setattr(api_main, "LocationCache", _FakeLocationCache)
    monkeypatch.setattr(api_main, "ProductImageCache", _FakeProductImageCache)
    monkeypatch.setattr(
        api_routes.requests, "get", lambda *args, **kwargs: _EmptyResponse()
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
