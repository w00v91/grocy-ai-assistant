from grocy_ai_assistant.api import routes


def test_shopping_list_returns_items(client, monkeypatch):
    def fake_get_shopping_list(self):
        return [
            {
                "id": 11,
                "amount": "2",
                "product_name": "Hafermilch",
                "note": "Barista",
                "picture_url": "https://example.org/hafermilch.png",
            }
        ]

    monkeypatch.setattr(routes.GrocyClient, "get_shopping_list", fake_get_shopping_list)
    response = client.get(
        "/api/dashboard/shopping-list",
        headers={"Authorization": "Bearer test-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 11,
            "amount": "2",
            "product_name": "Hafermilch",
            "note": "Barista",
            "picture_url": "https://example.org/hafermilch.png",
        }
    ]


def test_dashboard_prefills_configured_api_key(client):
    response = client.get("/")

    assert response.status_code == 200
    assert 'const configuredApiKey = "test-api-key";' in response.text
    assert "prompt('Bitte API-Key eingeben:'" not in response.text


def test_dashboard_has_mobile_friendly_layout_rules(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "@media (max-width: 640px)" in response.text
    assert "min-height: 44px;" in response.text
    assert "flex-direction: column;" in response.text
