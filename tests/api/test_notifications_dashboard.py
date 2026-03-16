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


def test_notification_overview_discovers_mobile_devices_via_homeassistant_services(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    class _Response:
        status_code = 200

        @staticmethod
        def json():
            return [
                {
                    "domain": "notify",
                    "services": {
                        "mobile_app_pixel_9": {},
                        "persistent_notification": {},
                    },
                }
            ]

    def _fake_get(url, headers=None, timeout=None):
        return _Response()

    monkeypatch.setattr(routes.requests, "get", _fake_get)

    response = client.get(
        "/api/dashboard/notifications/overview",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["devices"]
    assert payload["devices"][0]["service"] == "notify.mobile_app_pixel_9"


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


def test_notification_settings_are_user_scoped(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )

    update_response = client.put(
        "/api/dashboard/notifications/settings",
        headers={
            "Authorization": "Bearer test-api-key",
            "X-HA-User-Id": "user-a",
        },
        json={
            "enabled": True,
            "enabled_event_types": ["shopping_due"],
            "default_channels": ["persistent_notification"],
            "default_severity": "critical",
        },
    )
    assert update_response.status_code == 200

    user_a_overview = client.get(
        "/api/dashboard/notifications/overview",
        headers={
            "Authorization": "Bearer test-api-key",
            "X-HA-User-Id": "user-a",
        },
    )
    user_b_overview = client.get(
        "/api/dashboard/notifications/overview",
        headers={
            "Authorization": "Bearer test-api-key",
            "X-HA-User-Id": "user-b",
        },
    )

    assert user_a_overview.status_code == 200
    assert user_b_overview.status_code == 200
    assert user_a_overview.json()["settings"]["default_severity"] == "critical"
    assert user_b_overview.json()["settings"]["default_severity"] == "info"


def test_notification_defaults_include_multiple_sensible_rules(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )

    response = client.get(
        "/api/dashboard/notifications/overview",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    rule_names = {rule["name"] for rule in payload["rules"]}
    assert {"Einkauf fällig", "Niedriger Bestand", "Fehlende Rezept-Zutaten"}.issubset(
        rule_names
    )


def test_notification_rule_modal_uses_dropdowns_for_events_and_devices(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "<select id='notify-rule-events' multiple></select>" in response.text
    assert "<select id='notify-rule-devices' multiple></select>" in response.text
    assert "id='notify-rule-submit-button'" in response.text
    assert "onclick='saveNotificationRule()'" in response.text


def test_notification_persistent_test_calls_home_assistant_service(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    called = {}

    class _Response:
        status_code = 200

    def _fake_post(url, headers=None, json=None, timeout=None):
        called["url"] = url
        called["headers"] = headers or {}
        called["json"] = json or {}
        called["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/persistent",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert called["url"].endswith("/core/api/services/persistent_notification/create")
    assert called["json"]["title"] == "Testbenachrichtigung"


def test_notification_persistent_test_returns_error_when_supervisor_token_missing(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    monkeypatch.delenv("HASSIO_TOKEN", raising=False)

    class _Response:
        status_code = 401
        text = "Unauthorized"

    def _fake_post(url, headers=None, json=None, timeout=None):
        return _Response()

    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/persistent",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 502
    assert "Home-Assistant-Autorisierung fehlgeschlagen" in response.text

    overview = client.get(
        "/api/dashboard/notifications/overview",
        headers={"Authorization": "Bearer test-api-key"},
    )
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["history"]
    assert payload["history"][0]["delivered"] is False
    assert "Autorisierung fehlgeschlagen" in payload["history"][0]["error"]


def test_notification_persistent_test_uses_hassio_token_when_supervisor_missing(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    monkeypatch.setenv("HASSIO_TOKEN", "hassio-token")

    called = {}

    class _Response:
        status_code = 200
        text = ""

    def _fake_post(url, headers=None, json=None, timeout=None):
        called["headers"] = headers or {}
        return _Response()

    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/persistent",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert called["headers"]["Authorization"] == "Bearer hassio-token"


def test_notification_persistent_test_sanitizes_notification_id(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    called = {}

    class _Response:
        status_code = 200
        text = ""

    def _fake_post(url, headers=None, json=None, timeout=None):
        called["json"] = json or {}
        return _Response()

    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/persistent",
        headers={
            "Authorization": "Bearer test-api-key",
            "x-ha-user-id": "abc:def/ghi",
        },
    )

    assert response.status_code == 200
    assert called["json"]["notification_id"] == "dashboard-test-abc-def-ghi"


def test_notification_persistent_test_retries_without_notification_id_on_422(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    calls = []

    class _Response:
        def __init__(self, status_code, text=""):
            self.status_code = status_code
            self.text = text

    def _fake_post(url, headers=None, json=None, timeout=None):
        payload = json or {}
        calls.append(payload)
        if "notification_id" in payload:
            return _Response(422, "invalid notification_id")
        return _Response(200)

    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/persistent",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert calls
    assert "notification_id" in calls[0]
    assert any("notification_id" not in payload for payload in calls)


def test_notification_persistent_test_falls_back_to_notify_on_core_400(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    calls = []

    class _Response:
        def __init__(self, status_code, text=""):
            self.status_code = status_code
            self.text = text

    def _fake_post(url, headers=None, json=None, timeout=None):
        calls.append((url, json or {}))
        if "/persistent_notification/create" in url:
            return _Response(400, "Service persistent_notification.create not found")
        return _Response(200)

    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/persistent",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert any("/persistent_notification/create" in url for url, _ in calls)
    fallback_calls = [
        payload for url, payload in calls if "/notify/persistent_notification" in url
    ]
    assert fallback_calls
    assert "notification_id" not in fallback_calls[0]


def test_notification_persistent_test_uses_x_hassio_key_header_when_required(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    called_headers = []

    class _Response:
        def __init__(self, status_code, text=""):
            self.status_code = status_code
            self.text = text

    def _fake_post(url, headers=None, json=None, timeout=None):
        headers = headers or {}
        called_headers.append(headers)
        if headers.get("X-Hassio-Key") == "token":
            return _Response(200)
        return _Response(401, "Unauthorized")

    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/persistent",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert any(h.get("X-Hassio-Key") == "token" for h in called_headers)


def test_notification_mobile_test_all_calls_notify_services(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    class _GetResponse:
        status_code = 200

        @staticmethod
        def json():
            return [
                {
                    "domain": "notify",
                    "services": {
                        "mobile_app_samsung_s23": {},
                    },
                }
            ]

    called_posts = []

    class _PostResponse:
        status_code = 200
        text = ""

    def _fake_get(url, headers=None, timeout=None):
        return _GetResponse()

    def _fake_post(url, headers=None, json=None, timeout=None):
        called_posts.append((url, json or {}))
        return _PostResponse()

    monkeypatch.setattr(routes.requests, "get", _fake_get)
    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/all",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["sent_to"] == 1
    assert any(
        "/api/services/notify/mobile_app_samsung_s23" in url for url, _ in called_posts
    )


def test_notification_mobile_test_device_returns_error_on_service_failure(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        routes, "NOTIFICATION_STORAGE_PATH", tmp_path / "notification_dashboard.json"
    )
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    class _GetResponse:
        status_code = 200

        @staticmethod
        def json():
            return [
                {
                    "domain": "notify",
                    "services": {
                        "mobile_app_samsung_s23": {},
                    },
                }
            ]

    class _PostResponse:
        status_code = 404
        text = "Service not found"

    def _fake_get(url, headers=None, timeout=None):
        return _GetResponse()

    def _fake_post(url, headers=None, json=None, timeout=None):
        return _PostResponse()

    monkeypatch.setattr(routes.requests, "get", _fake_get)
    monkeypatch.setattr(routes.requests, "post", _fake_post)

    response = client.post(
        "/api/dashboard/notifications/tests/device",
        headers={"Authorization": "Bearer test-api-key"},
        json={"target_id": "notify.mobile_app_samsung_s23"},
    )

    assert response.status_code == 502
    assert "Notify-Service" in response.text
