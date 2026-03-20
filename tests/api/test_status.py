def test_status_requires_authorization(client):
    response = client.get("/api/status")

    assert response.status_code == 401
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["message"] == "Unauthorized"
    assert payload["error"]["code"] == "unauthorized"


def test_health_is_reachable_without_authorization(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_status_returns_ok_when_authorized(client):
    response = client.get(
        "/api/status",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Verbunden"
    assert response.json()["ollama_ready"] is True


def test_health_returns_ok_when_authorized(client):
    response = client.get(
        "/api/v1/health",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "status": "ok",
        "service": "grocy_ai_assistant",
        "addon_version": "2026.03.0",
        "required_integration_version": "1.2.10",
    }


def test_capabilities_is_reachable_without_authorization(client):
    response = client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json()["api_version"] == "v1"


def test_status_returns_homeassistant_compatible_payload(client):
    response = client.get(
        "/api/status",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "Verbunden",
        "ollama_ready": True,
        "addon_version": "2026.03.0",
        "required_integration_version": "1.2.10",
        "homeassistant_restart_required": False,
        "update_reason": "",
    }


def test_status_requires_homeassistant_restart_when_integration_version_differs(client):
    response = client.get(
        "/api/status",
        headers={
            "Authorization": "Bearer test-api-key",
            "X-HA-Integration-Version": "1.2.9",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["homeassistant_restart_required"] is True
    assert payload["required_integration_version"] == "1.2.10"
    assert payload["update_reason"] == (
        "Installierte Integration 1.2.9 weicht von der benötigten Version 1.2.10 ab."
    )


def test_capabilities_exposes_supported_v1_contract(client):
    response = client.get(
        "/api/v1/capabilities",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    assert payload["api_version"] == "v1"
    assert payload["service"] == "grocy_ai_assistant"
    assert payload["features"]["scan_image"] is True
    assert payload["features"]["grocy_sync"] is True
    assert "/api/v1/grocy/sync" in payload["endpoints"]
    assert "/api/v1/scan/image" in payload["endpoints"]


def test_v1_status_mirrors_legacy_status_payload(client):
    response = client.get(
        "/api/v1/status",
        headers={
            "Authorization": "Bearer test-api-key",
            "X-HA-Integration-Version": "1.2.9",
        },
    )

    assert response.status_code == 200
    assert response.json()["homeassistant_restart_required"] is True
