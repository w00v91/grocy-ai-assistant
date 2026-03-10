from grocy_ai_assistant.config.settings import Settings
from grocy_ai_assistant.services.product_image_cache import ProductImageCache


def test_get_cached_image_downloads_and_reads(monkeypatch, tmp_path):
    settings = Settings(grocy_base_url="http://homeassistant.local:9192/api", grocy_api_key="x")
    cache = ProductImageCache(settings, cache_dir=str(tmp_path))

    class FakeResponse:
        content = b"img-bytes"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        "grocy_ai_assistant.services.product_image_cache.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    content, media_type = cache.get_cached_image(
        "http://homeassistant.local:9192/files/productpictures/milk.png"
    )

    assert content == b"img-bytes"
    assert media_type == "image/png"


def test_refresh_all_product_images_downloads_only_with_picture(monkeypatch, tmp_path):
    settings = Settings(grocy_base_url="http://homeassistant.local:9192/api", grocy_api_key="x")
    cache = ProductImageCache(settings, cache_dir=str(tmp_path))

    products_payload = [{"id": 1, "picture_file_name": "a.jpg"}, {"id": 2, "name": "NoPic"}]

    class FakeResponse:
        def __init__(self, payload=None, content=b"img"):
            self._payload = payload
            self.content = content

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    calls = {"download": 0}

    def fake_get(url, headers, timeout):
        if url.endswith("/objects/products"):
            return FakeResponse(payload=products_payload)
        calls["download"] += 1
        return FakeResponse(content=b"img")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.product_image_cache.requests.get", fake_get
    )

    refreshed = cache.refresh_all_product_images()

    assert refreshed == 1
    assert calls["download"] == 1


def test_download_to_cache_falls_back_from_api_files_path(monkeypatch, tmp_path):
    settings = Settings(grocy_base_url="http://homeassistant.local:9192/api", grocy_api_key="x")
    cache = ProductImageCache(settings, cache_dir=str(tmp_path))

    class FakeResponse:
        def __init__(self, status_code=200, content=b"img"):
            self.status_code = status_code
            self.content = content

        def raise_for_status(self):
            if self.status_code >= 400:
                import requests

                error = requests.HTTPError("not found")
                error.response = self
                raise error

    calls = []

    def fake_get(url, headers, timeout):
        calls.append(url)
        if "/api/files/" in url:
            return FakeResponse(status_code=404)
        return FakeResponse(content=b"fallback-img")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.product_image_cache.requests.get", fake_get
    )

    content, media_type = cache.get_cached_image(
        "http://homeassistant.local:9192/api/files/productpictures/milk.png"
    )

    assert content == b"fallback-img"
    assert media_type == "image/png"
    assert calls == [
        "http://homeassistant.local:9192/api/files/productpictures/milk.png",
        "http://homeassistant.local:9192/files/productpictures/milk.png",
    ]
