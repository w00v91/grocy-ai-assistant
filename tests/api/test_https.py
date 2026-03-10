from grocy_ai_assistant.api.main import _is_external_host


def test_is_external_host_detection():
    assert _is_external_host("example.org") is True
    assert _is_external_host("8.8.8.8") is True
    assert _is_external_host("localhost:8000") is False
    assert _is_external_host("192.168.1.5:8123") is False


def test_redirects_external_http_to_https(client):
    response = client.get(
        "/",
        headers={"host": "example.org"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://example.org/")


def test_does_not_redirect_internal_http(client):
    response = client.get(
        "/",
        headers={"host": "localhost:8000"},
    )

    assert response.status_code == 200


def test_dashboard_contains_https_upgrade_logic(client):
    response = client.get("/", headers={"host": "localhost:8000"})
    js_response = client.get(
        "/dashboard-static/dashboard.js", headers={"host": "localhost:8000"}
    )

    assert response.status_code == 200
    assert js_response.status_code == 200
    assert "window.location.protocol === 'https:'" in js_response.text
    assert "new URL(url).host !== window.location.host" in js_response.text
