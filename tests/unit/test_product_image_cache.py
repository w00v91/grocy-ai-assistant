from grocy_ai_assistant.config.settings import Settings
from grocy_ai_assistant.services.product_image_cache import ProductImageCache




def test_product_image_cache_start_skips_background_thread_without_grocy_key(tmp_path):
    cache = ProductImageCache(
        Settings(grocy_api_key=""),
        cache_dir=str(tmp_path),
        refresh_interval_seconds=3600,
    )

    cache.start()
    try:
        assert cache._refresh_thread is None
        assert cache.wait_for_initial_refresh(timeout=0.1) is True
    finally:
        cache.stop()


def test_get_cached_image_downloads_and_reads(monkeypatch, tmp_path):
    settings = Settings(
        grocy_base_url="http://homeassistant.local:9192/api", grocy_api_key="x"
    )
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
        "http://homeassistant.local:9192/files/productpictures/bWlsay5wbmc="
    )

    assert content == b"img-bytes"
    assert media_type == "image/png"


def test_refresh_all_product_images_downloads_only_with_picture(monkeypatch, tmp_path):
    settings = Settings(
        grocy_base_url="http://homeassistant.local:9192/api", grocy_api_key="x"
    )
    cache = ProductImageCache(settings, cache_dir=str(tmp_path))

    products_payload = [
        {"id": 1, "picture_file_name": "a.jpg"},
        {"id": 2, "name": "NoPic"},
    ]

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
    settings = Settings(
        grocy_base_url="http://homeassistant.local:9192/api", grocy_api_key="x"
    )
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
        "http://homeassistant.local:9192/api/files/productpictures/bWlsay5wbmc="
    )

    assert content == b"fallback-img"
    assert media_type == "image/png"
    assert calls == [
        "http://homeassistant.local:9192/api/files/productpictures/bWlsay5wbmc=",
        "http://homeassistant.local:9192/files/productpictures/bWlsay5wbmc=",
    ]


def test_refresh_all_product_images_falls_back_to_picture_file_name(
    monkeypatch, tmp_path
):
    settings = Settings(
        grocy_base_url="http://homeassistant.local:9192/api", grocy_api_key="x"
    )
    cache = ProductImageCache(settings, cache_dir=str(tmp_path))

    products_payload = [
        {
            "id": 1,
            "picture_url": "files/productpictures/40b3s07zk17fd14nuym0i8chiasamen.jpg",
            "picture_file_name": "chiasamen.jpg",
        }
    ]

    class FakeResponse:
        def __init__(self, payload=None, content=b"img", status_code=200):
            self._payload = payload
            self.content = content
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                import requests

                error = requests.HTTPError("not found")
                error.response = self
                raise error

        def json(self):
            return self._payload

    download_calls = []

    def fake_get(url, headers, timeout):
        if url.endswith("/objects/products"):
            return FakeResponse(payload=products_payload)
        download_calls.append(url)
        if "NDBiM3MwN3prMTdmZDE0bnV5bTBpOGNoaWFzYW1lbi5qcGc=" in url:
            return FakeResponse(status_code=404)
        return FakeResponse(content=b"fallback-img")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.product_image_cache.requests.get", fake_get
    )

    refreshed = cache.refresh_all_product_images()

    assert refreshed == 1
    assert download_calls == [
        "http://homeassistant.local:9192/api/files/productpictures/NDBiM3MwN3prMTdmZDE0bnV5bTBpOGNoaWFzYW1lbi5qcGc=",
        "http://homeassistant.local:9192/files/productpictures/NDBiM3MwN3prMTdmZDE0bnV5bTBpOGNoaWFzYW1lbi5qcGc=",
        "http://homeassistant.local:9192/api/files/productpictures/Y2hpYXNhbWVuLmpwZw==",
    ]


def test_download_to_cache_falls_back_from_files_path_to_api_files(
    monkeypatch, tmp_path
):
    settings = Settings(
        grocy_base_url="http://homeassistant.local:9192/api", grocy_api_key="x"
    )
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
        if "/files/" in url and "/api/files/" not in url:
            return FakeResponse(status_code=404)
        return FakeResponse(content=b"api-fallback-img")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.product_image_cache.requests.get", fake_get
    )

    content, media_type = cache.get_cached_image(
        "http://homeassistant.local:9192/files/productpictures/cXVpbm9hLnBuZw=="
    )

    assert content == b"api-fallback-img"
    assert media_type == "image/png"
    assert calls == [
        "http://homeassistant.local:9192/files/productpictures/cXVpbm9hLnBuZw==",
        "http://homeassistant.local:9192/api/files/productpictures/cXVpbm9hLnBuZw==",
    ]
