from grocy_ai_assistant.config.settings import Settings
from grocy_ai_assistant.services.location_cache import LocationCache


def test_location_cache_start_skips_background_thread_without_grocy_key():
    cache = LocationCache(Settings(grocy_api_key=""), refresh_interval_seconds=3600)

    cache.start()
    try:
        assert cache._refresh_thread is None
    finally:
        cache.stop()
