def test_status_requires_authorization(client):
    response = client.get("/api/status")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_status_returns_ok_when_authorized(client):
    response = client.get(
        "/api/status",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Verbunden"
    assert response.json()["ollama_ready"] is True
def test_status_returns_homeassistant_compatible_payload(client):
    response = client.get(
        '/api/status',
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "Verbunden",
        "ollama_ready": True,
        "addon_version": "2026.03.0",
        "required_integration_version": "1.2.8",
        "homeassistant_restart_required": False,
        "update_reason": "",
    }


def test_status_requires_homeassistant_restart_when_integration_version_differs(client):
    response = client.get(
        '/api/status',
        headers={
            "Authorization": "Bearer test-api-key",
            "X-HA-Integration-Version": "1.2.6",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["homeassistant_restart_required"] is True
    assert payload["required_integration_version"] == "1.2.8"
    assert payload["update_reason"] == (
        "Installierte Integration 1.2.6 weicht von der benötigten Version 1.2.8 ab."
    )
