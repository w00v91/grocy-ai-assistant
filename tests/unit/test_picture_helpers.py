from grocy_ai_assistant.api.routes import (
    _build_dashboard_picture_proxy_url,
    _build_product_picture_url,
)
from grocy_ai_assistant.config.settings import Settings
from grocy_ai_assistant.core.picture_urls import build_product_picture_url


SETTINGS = Settings(
    api_key="x",
    addon_version="a",
    required_integration_version="1.2.10",
    grocy_api_key="g",
)


def test_build_product_picture_url_supports_filename_relative_and_absolute_paths():
    assert _build_product_picture_url("milk.jpg", SETTINGS).endswith(
        "/files/productpictures/bWlsay5qcGc="
    )
    assert _build_product_picture_url(
        "files/productpictures/milk.jpg", SETTINGS
    ).endswith("/files/productpictures/bWlsay5qcGc=")
    assert _build_product_picture_url("/custom/path/image.jpg", SETTINGS).endswith(
        "/custom/path/image.jpg"
    )


def test_build_product_picture_url_keeps_external_absolute_or_data_urls():
    https_url = "https://cdn.example.com/image.png"
    data_url = "data:image/png;base64,abc"

    assert _build_product_picture_url(https_url, SETTINGS) == https_url
    assert _build_product_picture_url(data_url, SETTINGS) == data_url


def test_build_product_picture_url_rewrites_localhost_host_to_configured_grocy_host():
    localhost_url = "http://localhost:9192/files/productpictures/milk.jpg"

    rewritten = _build_product_picture_url(localhost_url, SETTINGS)

    assert (
        rewritten
        == "http://homeassistant.local:9192/files/productpictures/bWlsay5qcGc="
    )


def test_build_dashboard_picture_proxy_url_encodes_absolute_url():
    proxy_url = _build_dashboard_picture_proxy_url("milk.jpg", SETTINGS)

    assert proxy_url.startswith("/api/dashboard/product-picture?src=")
    assert "files%2Fproductpictures%2FbWlsay5qcGc%3D" in proxy_url
    assert "size=thumb" in proxy_url


def test_shared_picture_helper_matches_route_behavior():
    value = "files/productpictures/tomate.png"

    assert build_product_picture_url(value, SETTINGS) == _build_product_picture_url(
        value, SETTINGS
    )
