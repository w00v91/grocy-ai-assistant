from fastapi.testclient import TestClient

import grocy_ai_assistant.api.main as api_main
from grocy_ai_assistant.config.settings import Settings


class _DummyCache:
    def __init__(self, _settings):
        pass

    def start(self):
        return None

    def stop(self):
        return None


def test_startup_prefetch_waits_five_seconds(monkeypatch):
    calls: list[object] = []

    async def fake_sleep(seconds: float):
        calls.append(seconds)

    def fake_prefetch(_settings):
        calls.append("prefetch")
        return None

    monkeypatch.setattr(api_main, "ProductImageCache", _DummyCache)
    monkeypatch.setattr(api_main, "LocationCache", _DummyCache)
    monkeypatch.setattr(api_main.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(api_main, "prefetch_initial_recipe_suggestions", fake_prefetch)
    monkeypatch.setattr(
        api_main,
        "get_settings",
        lambda: Settings(api_key="k", grocy_api_key="g"),
    )

    app = api_main.create_app()
    with TestClient(app):
        pass

    assert calls[0] == 5
    assert "prefetch" in calls


def test_startup_batch_generates_images_for_products_without_picture(monkeypatch):
    attached: list[tuple[int, str]] = []

    class DummyGrocyClient:
        def __init__(self, _settings):
            pass

        def get_products_without_picture(self):
            return [
                {"id": 1, "name": "Nudeln"},
                {"id": "2", "name": "Tomatensauce"},
            ]

        def attach_product_picture(self, product_id: int, image_path: str):
            attached.append((product_id, image_path))

    class DummyDetector:
        def __init__(self, _settings):
            pass

        def generate_product_image(self, product_name: str) -> str:
            return f"/tmp/{product_name}.png"

    monkeypatch.setattr(api_main, "GrocyClient", DummyGrocyClient)
    monkeypatch.setattr(api_main, "IngredientDetector", DummyDetector)

    settings = Settings(
        api_key="k",
        grocy_api_key="g",
        image_generation_enabled=True,
        generate_missing_product_images_on_startup=True,
    )

    api_main._generate_missing_product_images_on_startup(settings)

    assert attached == [(1, "/tmp/Nudeln.png"), (2, "/tmp/Tomatensauce.png")]


def test_startup_batch_skips_when_flag_disabled(monkeypatch):
    class DummyGrocyClient:
        def __init__(self, _settings):
            raise AssertionError("should not be created")

    monkeypatch.setattr(api_main, "GrocyClient", DummyGrocyClient)

    settings = Settings(
        api_key="k",
        grocy_api_key="g",
        image_generation_enabled=True,
        generate_missing_product_images_on_startup=False,
    )

    api_main._generate_missing_product_images_on_startup(settings)
