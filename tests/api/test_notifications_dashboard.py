from grocy_ai_assistant.api import routes


def test_dashboard_contains_notification_tab(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "tab-button-notifications" in response.text
    assert "Benachrichtigungen" in response.text


def test_notification_overview_returns_defaults(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )

    response = client.get(
        "/api/dashboard/notifications/overview",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["settings"]["enabled"] is True
    assert isinstance(payload["rules"], list)
    assert payload["rules"][0]["name"]


def test_notification_rule_can_be_created_and_deleted(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )

    create_response = client.post(
        "/api/dashboard/notifications/rules",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "name": "Meine Regel",
            "enabled": True,
            "event_types": ["shopping_due"],
            "target_user_ids": [],
            "target_device_ids": [],
            "channels": ["mobile_push"],
            "severity": "info",
            "cooldown_seconds": 30,
            "quiet_hours_start": "",
            "quiet_hours_end": "",
            "conditions": [],
            "message_template": "${message}",
        },
    )

    assert create_response.status_code == 200
    created_rule = create_response.json()
    delete_response = client.delete(
        f"/api/dashboard/notifications/rules/{created_rule['id']}",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
