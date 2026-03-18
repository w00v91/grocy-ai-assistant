import json

from fastapi.testclient import TestClient

import grocy_ai_assistant.api.main as api_main
from grocy_ai_assistant.config import options_store
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

    def fake_wait_for_initial_refresh(self, timeout=None):
        calls.append("wait_for_image_sync")
        return True

    monkeypatch.setattr(api_main, "ProductImageCache", _DummyCache)
    monkeypatch.setattr(api_main, "LocationCache", _DummyCache)
    monkeypatch.setattr(api_main.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(api_main, "prefetch_initial_recipe_suggestions", fake_prefetch)
    monkeypatch.setattr(
        _DummyCache,
        "wait_for_initial_refresh",
        fake_wait_for_initial_refresh,
        raising=False,
    )
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


def test_product_image_cache_wait_for_initial_refresh_signals_after_refresh(
    monkeypatch,
):
    from grocy_ai_assistant.services.product_image_cache import ProductImageCache

    class _ImmediateSettings:
        grocy_api_key = "g"
        grocy_base_url = "http://localhost:9192/api"

    cache = ProductImageCache(_ImmediateSettings(), refresh_interval_seconds=3600)
    monkeypatch.setattr(cache, "refresh_all_product_images", lambda: 0)

    cache.start()
    try:
        assert cache.wait_for_initial_refresh(timeout=1.0) is True
    finally:
        cache.stop()


def test_startup_batch_disables_option_after_completion(monkeypatch, tmp_path):
    options_path = tmp_path / "options.yaml"
    options_path.write_text(
        "generate_missing_product_images_on_startup: true\n"
        "initial_info_sync: true\n",
        encoding="utf-8",
    )

    class DummyGrocyClient:
        def __init__(self, _settings):
            pass

        def get_products_without_picture(self):
            return [{"id": 1, "name": "Nudeln"}]

        def attach_product_picture(self, _product_id: int, _image_path: str):
            return None

    class DummyDetector:
        def __init__(self, _settings):
            pass

        def generate_product_image(self, product_name: str) -> str:
            return f"/tmp/{product_name}.png"

    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", options_path)
    monkeypatch.setattr(
        options_store,
        "LEGACY_ADDON_OPTIONS_JSON_PATH",
        tmp_path / "legacy-options.json",
    )
    monkeypatch.setattr(api_main, "GrocyClient", DummyGrocyClient)
    monkeypatch.setattr(api_main, "IngredientDetector", DummyDetector)

    settings = Settings(
        api_key="k",
        grocy_api_key="g",
        image_generation_enabled=True,
        generate_missing_product_images_on_startup=True,
        initial_info_sync=True,
    )

    api_main._generate_missing_product_images_on_startup(settings)

    stored = options_store.parse_simple_yaml(options_path.read_text(encoding="utf-8"))
    assert stored["generate_missing_product_images_on_startup"] is False
    assert stored["initial_info_sync"] is True


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


def test_startup_initial_info_sync_updates_missing_fields(monkeypatch, tmp_path):
    updated: list[dict] = []
    best_before_updates: list[tuple[int, int]] = []
    tmp_state_path = tmp_path / "initial-info-sync-state.json"
    tmp_options_path = tmp_path / "options.yaml"

    class DummyGrocyClient:
        def __init__(self, _settings):
            pass

        def get_products(self):
            return [
                {"id": 1, "name": "Nudeln", "default_best_before_days": None},
                {"id": 2, "name": "Milch", "default_best_before_days": 5},
            ]

        def get_product_nutrition(self, product_id: int):
            if product_id == 1:
                return {
                    "calories": "",
                    "carbs": "",
                    "fat": "",
                    "protein": "",
                    "sugar": "",
                }
            return {
                "calories": "120",
                "carbs": "10",
                "fat": "3",
                "protein": "7",
                "sugar": "",
            }

        def update_product_nutrition(self, **kwargs):
            updated.append(kwargs)

        def set_product_default_best_before_days(self, product_id: int, days: int):
            best_before_updates.append((product_id, days))

    class DummyDetector:
        def __init__(self, _settings):
            pass

        def analyze_product_name(self, product_name: str):
            if product_name == "Nudeln":
                return {
                    "calories": 350,
                    "carbohydrates": 70,
                    "fat": 2,
                    "protein": 12,
                    "sugar": 3,
                    "default_best_before_days": 365,
                }
            return {
                "calories": 0,
                "carbohydrates": 0,
                "fat": 0,
                "protein": 0,
                "sugar": 8,
                "default_best_before_days": 0,
            }

    monkeypatch.setattr(api_main, "GrocyClient", DummyGrocyClient)
    monkeypatch.setattr(api_main, "IngredientDetector", DummyDetector)
    monkeypatch.setattr(api_main, "INITIAL_INFO_SYNC_STATE_PATH", tmp_state_path)
    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", tmp_options_path)
    monkeypatch.setattr(
        options_store,
        "LEGACY_ADDON_OPTIONS_JSON_PATH",
        tmp_path / "legacy-options.json",
    )

    settings = Settings(
        api_key="k",
        grocy_api_key="g",
        initial_info_sync=True,
    )

    api_main._run_initial_info_sync_on_startup(settings)

    assert updated == [
        {
            "product_id": 1,
            "calories": 350.0,
            "carbs": 70.0,
            "fat": 2.0,
            "protein": 12.0,
            "sugar": 3.0,
        },
        {
            "product_id": 2,
            "calories": None,
            "carbs": None,
            "fat": None,
            "protein": None,
            "sugar": 8.0,
        },
    ]
    assert best_before_updates == [(1, 365)]


def test_startup_initial_info_sync_disables_option_after_completion(
    monkeypatch, tmp_path
):
    options_path = tmp_path / "options.yaml"
    options_path.write_text(
        "generate_missing_product_images_on_startup: true\n"
        "initial_info_sync: true\n",
        encoding="utf-8",
    )

    class DummyGrocyClient:
        def __init__(self, _settings):
            pass

        def get_products(self):
            return [{"id": 1, "name": "Nudeln", "default_best_before_days": None}]

        def get_product_nutrition(self, _product_id: int):
            return {
                "calories": "",
                "carbs": "",
                "fat": "",
                "protein": "",
                "sugar": "",
            }

        def update_product_nutrition(self, **_kwargs):
            return None

        def set_product_default_best_before_days(self, _product_id: int, _days: int):
            return None

    class DummyDetector:
        def __init__(self, _settings):
            pass

        def analyze_product_name(self, _product_name: str):
            return {
                "calories": 350,
                "carbohydrates": 70,
                "fat": 2,
                "protein": 12,
                "sugar": 3,
                "default_best_before_days": 365,
            }

    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", options_path)
    monkeypatch.setattr(
        options_store,
        "LEGACY_ADDON_OPTIONS_JSON_PATH",
        tmp_path / "legacy-options.json",
    )
    monkeypatch.setattr(api_main, "GrocyClient", DummyGrocyClient)
    monkeypatch.setattr(api_main, "IngredientDetector", DummyDetector)

    settings = Settings(
        api_key="k",
        grocy_api_key="g",
        initial_info_sync=True,
        generate_missing_product_images_on_startup=True,
    )

    api_main._run_initial_info_sync_on_startup(settings)

    stored = options_store.parse_simple_yaml(options_path.read_text(encoding="utf-8"))
    assert stored["initial_info_sync"] is False
    assert stored["generate_missing_product_images_on_startup"] is True


def test_startup_initial_info_sync_skips_when_flag_disabled(monkeypatch):
    class DummyGrocyClient:
        def __init__(self, _settings):
            raise AssertionError("should not be created")

    monkeypatch.setattr(api_main, "GrocyClient", DummyGrocyClient)

    settings = Settings(
        api_key="k",
        grocy_api_key="g",
        initial_info_sync=False,
    )

    api_main._run_initial_info_sync_on_startup(settings)


def test_startup_initial_info_sync_uses_delta_state_to_skip_unchanged_products(
    monkeypatch, tmp_path
):
    nutrition_calls: list[int] = []

    unchanged_product = {
        "id": 1,
        "name": "Reis",
        "default_best_before_days": 365,
        "row_updated_timestamp": "2026-03-17 10:00:00",
    }
    candidate_product = {
        "id": 2,
        "name": "Milch",
        "default_best_before_days": None,
        "row_updated_timestamp": "2026-03-17 10:01:00",
    }

    state_path = tmp_path / "initial-info-sync-state.json"
    state_path.write_text(
        json.dumps(
            {
                "1": {
                    "signature": api_main._build_initial_sync_product_signature(
                        unchanged_product
                    ),
                    "missing_fields": False,
                }
            }
        ),
        encoding="utf-8",
    )

    class DummyGrocyClient:
        def __init__(self, _settings):
            pass

        def get_products(self):
            return [unchanged_product, candidate_product]

        def get_product_nutrition(self, product_id: int):
            nutrition_calls.append(product_id)
            return {
                "calories": "",
                "carbs": "",
                "fat": "",
                "protein": "",
                "sugar": "",
            }

        def update_product_nutrition(self, **_kwargs):
            return None

        def set_product_default_best_before_days(self, _product_id: int, _days: int):
            return None

    class DummyDetector:
        def __init__(self, _settings):
            pass

        def analyze_product_name(self, _product_name: str):
            return {
                "calories": 120,
                "carbohydrates": 10,
                "fat": 4,
                "protein": 6,
                "sugar": 4,
                "default_best_before_days": 7,
            }

    monkeypatch.setattr(api_main, "INITIAL_INFO_SYNC_STATE_PATH", state_path)
    monkeypatch.setattr(api_main, "GrocyClient", DummyGrocyClient)
    monkeypatch.setattr(api_main, "IngredientDetector", DummyDetector)

    settings = Settings(api_key="k", grocy_api_key="g", initial_info_sync=True)
    api_main._run_initial_info_sync_on_startup(settings)

    assert nutrition_calls == [2]
