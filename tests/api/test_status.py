from grocy_ai_assistant.config.settings import get_settings


def test_status_requires_authorization(client):
    response = client.get("/api/status")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_status_returns_ok_when_authorized(client):
    settings = get_settings()
    response = client.get(
        "/api/status",
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Verbunden"
    assert response.json()["ollama_ready"] is True
