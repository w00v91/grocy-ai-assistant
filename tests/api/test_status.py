from grocy_ai_assistant.api import main


def test_status_requires_authorization(client):
    response = client.get('/api/status')

    assert response.status_code == 401
    assert response.get_json() == {"status": "Nicht autorisiert"}


def test_status_returns_ok_when_authorized(client):
    response = client.get(
        '/api/status',
        headers={"Authorization": f"Bearer {main.EXPECTED_API_KEY}"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "Verbunden", "ollama_ready": True}
