import pytest
from requests import HTTPError

from grocy_ai_assistant.config.settings import Settings
from grocy_ai_assistant.services.grocy_client import GrocyClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_find_product_by_name_returns_exact_match(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(
            [
                {"id": 1, "name": "Mozzarella"},
                {"id": 2, "name": "Gouda"},
            ]
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    assert client.find_product_by_name("mozzarella") == {"id": 1, "name": "Mozzarella"}


def test_find_product_by_name_returns_vector_match_for_typo(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(
            [
                {"id": 1, "name": "Mozzarella"},
                {"id": 2, "name": "Butter"},
            ]
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    assert client.find_product_by_name("mozarella") == {"id": 1, "name": "Mozzarella"}


def test_find_product_by_name_returns_none_when_similarity_is_too_low(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(
            [
                {"id": 1, "name": "Mozzarella"},
                {"id": 2, "name": "Butter"},
            ]
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    assert client.find_product_by_name("schraubenzieher") is None


def test_get_shopping_list_falls_back_to_objects_endpoint(monkeypatch):
    class FailingStockResponse(FakeResponse):
        status_code = 405

        def raise_for_status(self):
            raise HTTPError("Method Not Allowed")

    requested_urls = []

    def fake_get(url, *args, **kwargs):
        requested_urls.append(url)
        if url.endswith("/stock/shoppinglist"):
            return FailingStockResponse([])
        if url.endswith("/objects/shopping_list"):
            return FakeResponse(
                [{"id": 7, "product_id": 10, "amount": 2, "note": "bio"}]
            )
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {
                        "id": 10,
                        "name": "Hafermilch",
                        "picture_url": "/api/files/hafer.jpg",
                    }
                ]
            )
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = client.get_shopping_list()

    assert requested_urls[0].endswith("/stock/shoppinglist")
    assert any(url.endswith("/objects/shopping_list") for url in requested_urls)
    assert result == [
        {
            "id": 7,
            "product_id": 10,
            "amount": 2,
            "note": "bio",
            "product_name": "Hafermilch",
            "picture_url": "/api/files/hafer.jpg",
        }
    ]


def test_get_shopping_list_uses_picture_file_name_if_picture_url_missing(monkeypatch):
    class FailingStockResponse(FakeResponse):
        status_code = 405

        def raise_for_status(self):
            raise HTTPError("Method Not Allowed")

    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock/shoppinglist"):
            return FailingStockResponse([])
        if url.endswith("/objects/shopping_list"):
            return FakeResponse([{"id": 8, "product_id": 11, "amount": 1, "note": ""}])
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {
                        "id": 11,
                        "name": "Tomaten",
                        "picture_file_name": "tomaten.jpg",
                    }
                ]
            )
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = client.get_shopping_list()

    assert result[0]["picture_url"] == "tomaten.jpg"


def test_get_shopping_list_sorts_stock_endpoint_by_newest_first(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock/shoppinglist"):
            return FakeResponse(
                [
                    {"id": 3, "product_name": "Alt", "row_created_timestamp": "2024-01-01 10:00:00"},
                    {"id": 5, "product_name": "Neu", "row_created_timestamp": "2024-01-01 11:00:00"},
                    {"id": 4, "product_name": "Ohne Zeit"},
                ]
            )
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = client.get_shopping_list()

    assert [item["id"] for item in result] == [5, 3, 4]


def test_get_shopping_list_sorts_objects_fallback_by_newest_first(monkeypatch):
    class FailingStockResponse(FakeResponse):
        status_code = 405

        def raise_for_status(self):
            raise HTTPError("Method Not Allowed")

    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock/shoppinglist"):
            return FailingStockResponse([])
        if url.endswith("/objects/shopping_list"):
            return FakeResponse(
                [
                    {"id": 7, "product_id": 10, "row_created_timestamp": "2024-01-01 08:00:00"},
                    {"id": 8, "product_id": 10, "row_created_timestamp": "2024-01-01 09:00:00"},
                    {"id": 6, "product_id": 10},
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse([{"id": 10, "name": "Hafermilch"}])
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = client.get_shopping_list()

    assert [item["id"] for item in result] == [8, 7, 6]


def test_get_shopping_list_raises_non_405_errors(monkeypatch):
    class UnauthorizedResponse(FakeResponse):
        status_code = 401

        def raise_for_status(self):
            raise HTTPError("Unauthorized")

    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock/shoppinglist"):
            return UnauthorizedResponse([])
        raise AssertionError(f"Unexpected fallback call: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    with pytest.raises(HTTPError):
        client.get_shopping_list()


def test_clear_shopping_list_deletes_all_items(monkeypatch):
    deleted_urls = []

    def fake_get_shopping_list(self):
        return [{"id": 3}, {"id": 4}, {"id": None}]

    def fake_delete(url, *args, **kwargs):
        deleted_urls.append(url)
        return FakeResponse({})

    monkeypatch.setattr(GrocyClient, "get_shopping_list", fake_get_shopping_list)
    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.delete", fake_delete
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    removed_items = client.clear_shopping_list()

    assert removed_items == 2
    assert deleted_urls == [
        "http://homeassistant.local:9192/api/objects/shopping_list/3",
        "http://homeassistant.local:9192/api/objects/shopping_list/4",
    ]


def test_search_products_by_partial_name_returns_all_variants(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(
            [
                {"id": 1, "name": "Apfel"},
                {"id": 2, "name": "Apfelessig"},
                {"id": 3, "name": "Banane"},
            ]
        )

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = client.search_products_by_partial_name("apf")

    assert [product["name"] for product in result] == ["Apfel", "Apfelessig"]


def test_get_stock_products_resolves_product_and_location_names(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {"product_id": 2, "amount": 3},
                    {"product_id": 1, "amount": 1},
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {"id": 1, "name": "Apfel", "location_id": 4},
                    {"id": 2, "name": "Milch", "location_id": 1},
                ]
            )
        if url.endswith("/objects/locations"):
            return FakeResponse(
                [
                    {"id": 1, "name": "Kühlschrank"},
                    {"id": 4, "name": "Obstkorb"},
                ]
            )
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = client.get_stock_products()

    assert result == [
        {
            "id": 1,
            "name": "Apfel",
            "location_id": 4,
            "location_name": "Obstkorb",
            "amount": "1",
        },
        {
            "id": 2,
            "name": "Milch",
            "location_id": 1,
            "location_name": "Kühlschrank",
            "amount": "3",
        },
    ]


def test_get_recipes_returns_grocy_recipes(monkeypatch):
    def fake_get(url, *args, **kwargs):
        assert url.endswith("/objects/recipes")
        return FakeResponse([{"id": 1, "name": "Pasta"}])

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    assert client.get_recipes() == [{"id": 1, "name": "Pasta"}]


def test_get_stock_products_filters_by_locations(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {"product_id": 2, "amount": 3},
                    {"product_id": 1, "amount": 1},
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {"id": 1, "name": "Apfel", "location_id": 4},
                    {"id": 2, "name": "Milch", "location_id": 1},
                ]
            )
        if url.endswith("/objects/locations"):
            return FakeResponse(
                [
                    {"id": 1, "name": "Kühlschrank"},
                    {"id": 4, "name": "Obstkorb"},
                ]
            )
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = client.get_stock_products([1])

    assert result == [
        {
            "id": 2,
            "name": "Milch",
            "location_id": 1,
            "location_name": "Kühlschrank",
            "amount": "3",
        },
    ]


def test_get_stock_products_uses_stock_location_for_filter_and_display(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {"product_id": "2", "location_id": "4", "amount": 1},
                    {"product_id": "3", "location_id": "1", "amount": 2},
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {"id": 2, "name": "Milch", "location_id": 1},
                    {"id": 3, "name": "Saft", "location_id": 4},
                ]
            )
        if url.endswith("/objects/locations"):
            return FakeResponse(
                [
                    {"id": 1, "name": "Kühlschrank"},
                    {"id": 4, "name": "Vorrat"},
                ]
            )
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.get", fake_get
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    result = client.get_stock_products([4])

    assert result == [
        {
            "id": 2,
            "name": "Milch",
            "location_id": 4,
            "location_name": "Vorrat",
            "amount": "1",
        }
    ]
