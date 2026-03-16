from base64 import b64encode
from datetime import datetime, timedelta

import pytest
import requests
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


def test_find_product_by_name_ignores_compound_prefix_match(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(
            [
                {"id": 1, "name": "Olivenöl"},
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

    assert client.find_product_by_name("Oliven") is None


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
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 10,
                        "location_id": 1,
                        "amount": "2",
                        "best_before_date": "2026-01-01",
                    }
                ]
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
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 10,
                        "location_id": 1,
                        "amount": "2",
                        "best_before_date": "2026-01-01",
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
    assert len(result) == 1
    assert result[0]["id"] == 7
    assert result[0]["product_id"] == 10
    assert result[0]["amount"] == 2
    assert result[0]["note"] == "bio"
    assert result[0]["product_name"] == "Hafermilch"
    assert result[0]["picture_url"] == "/api/files/hafer.jpg"


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
                    {
                        "id": 3,
                        "product_name": "Alt",
                        "row_created_timestamp": "2024-01-01 10:00:00",
                    },
                    {
                        "id": 5,
                        "product_name": "Neu",
                        "row_created_timestamp": "2024-01-01 11:00:00",
                    },
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
                    {
                        "id": 7,
                        "product_id": 10,
                        "row_created_timestamp": "2024-01-01 08:00:00",
                    },
                    {
                        "id": 8,
                        "product_id": 10,
                        "row_created_timestamp": "2024-01-01 09:00:00",
                    },
                    {"id": 6, "product_id": 10},
                ]
            )
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 10,
                        "location_id": 1,
                        "amount": "2",
                        "best_before_date": "2026-01-01",
                    }
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


def test_get_storage_products_can_include_products_not_in_stock(monkeypatch):
    def fake_stock_products(self, location_ids=None):
        return [
            {
                "id": 1,
                "stock_id": 77,
                "in_stock": True,
                "name": "Milch",
                "location_id": 1,
                "location_name": "Kühlschrank",
                "amount": "1",
                "best_before_date": "2026-01-01",
            }
        ]

    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {"id": 1, "name": "Milch", "location_id": 1},
                    {"id": 2, "name": "Nudeln", "location_id": 2},
                ]
            )
        if url.endswith("/objects/locations"):
            return FakeResponse(
                [
                    {"id": 1, "name": "Kühlschrank"},
                    {"id": 2, "name": "Vorrat"},
                ]
            )
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(GrocyClient, "get_stock_products", fake_stock_products)
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

    result = client.get_storage_products(include_all_products=True)

    assert [item["name"] for item in result] == ["Milch", "Nudeln"]
    assert result[1]["in_stock"] is False
    assert result[1]["amount"] == "0"


def test_get_stock_products_resolves_product_and_location_names(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 2,
                        "amount": 3,
                        "best_before_date_calculated": "2026-01-03",
                    },
                    {"product_id": 1, "amount": 1, "best_before_date": "2026-01-02"},
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
            "in_stock": True,
            "picture_url": "",
            "location_id": 4,
            "location_name": "Obstkorb",
            "amount": "1",
            "best_before_date": "2026-01-02",
            "calories": "",
            "carbs": "",
            "fat": "",
            "protein": "",
            "sugar": "",
        },
        {
            "id": 2,
            "name": "Milch",
            "in_stock": True,
            "picture_url": "",
            "location_id": 1,
            "location_name": "Kühlschrank",
            "amount": "3",
            "best_before_date": "2026-01-03",
            "calories": "",
            "carbs": "",
            "fat": "",
            "protein": "",
            "sugar": "",
        },
    ]


def test_get_stock_products_preserves_zero_amount_as_string(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 1,
                        "amount": 0,
                        "best_before_date": "",
                    }
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse([{"id": 1, "name": "Apfel", "location_id": 4}])
        if url.endswith("/objects/locations"):
            return FakeResponse([{"id": 4, "name": "Obstkorb"}])
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

    assert result[0]["amount"] == "0"


def test_get_recipes_returns_grocy_recipes(monkeypatch):
    def fake_get(url, *args, **kwargs):
        assert url.endswith("/objects/recipes")
        return FakeResponse(
            [
                {"id": 1, "name": "Pasta", "picture_file_name": "pasta.jpg"},
                {"id": 2, "name": "Suppe", "picture_url": "/img/suppe.jpg"},
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

    assert client.get_recipes() == [
        {
            "id": 1,
            "name": "Pasta",
            "picture_file_name": "pasta.jpg",
            "picture_url": "http://homeassistant.local:9192/api/files/recipepictures/cGFzdGEuanBn?force_serve_as=picture",
        },
        {
            "id": 2,
            "name": "Suppe",
            "picture_url": "/img/suppe.jpg",
        },
    ]


def test_get_recipes_rewrites_existing_recipe_picture_url(monkeypatch):
    def fake_get(url, *args, **kwargs):
        assert url.endswith("/objects/recipes")
        return FakeResponse(
            [
                {
                    "id": 1,
                    "name": "Salat",
                    "picture_url": "http://homeassistant.local:9192/api/files/recipepictures/ri3lsto844wuvkqsry4oidsc_0817-500x500.jpg",
                }
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

    assert client.get_recipes() == [
        {
            "id": 1,
            "name": "Salat",
            "picture_url": "http://homeassistant.local:9192/api/files/recipepictures/cmkzbHN0bzg0NHd1dmtxc3J5NG9pZHNjXzA4MTctNTAweDUwMC5qcGc=?force_serve_as=picture",
        }
    ]


def test_get_stock_products_filters_by_locations(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 2,
                        "amount": 3,
                        "best_before_date_calculated": "2026-01-03",
                    },
                    {"product_id": 1, "amount": 1, "best_before_date": "2026-01-02"},
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
            "in_stock": True,
            "picture_url": "",
            "location_id": 1,
            "location_name": "Kühlschrank",
            "amount": "3",
            "best_before_date": "2026-01-03",
            "calories": "",
            "carbs": "",
            "fat": "",
            "protein": "",
            "sugar": "",
        },
    ]


def test_get_stock_products_uses_stock_location_for_filter_and_display(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": "2",
                        "location_id": "4",
                        "amount": 1,
                        "best_before_date": "2026-01-10",
                    },
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
            "in_stock": True,
            "picture_url": "",
            "location_id": 4,
            "location_name": "Vorrat",
            "amount": "1",
            "best_before_date": "2026-01-10",
            "calories": "",
            "carbs": "",
            "fat": "",
            "protein": "",
            "sugar": "",
        }
    ]


def test_delete_shopping_list_item_calls_delete_object_endpoint(monkeypatch):
    captured = {}

    def fake_delete(url, *args, **kwargs):
        captured["url"] = url
        return FakeResponse({})

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

    client.delete_shopping_list_item(23, amount="2")

    assert captured["url"].endswith("/objects/shopping_list/23")


def test_update_shopping_list_item_amount_calls_put_endpoint(monkeypatch):
    captured = {}

    def fake_put(url, *args, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse({})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_shopping_list_item_amount(23, "4")

    assert captured["url"].endswith("/objects/shopping_list/23")
    assert captured["json"] == {"amount": "4"}


def test_update_shopping_list_item_best_before_date_calls_put_endpoint(monkeypatch):
    captured = {}

    def fake_put(url, *args, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse({})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_shopping_list_item_best_before_date(
        23,
        "2026-12-31",
        current_note="dringend",
    )

    assert captured["url"].endswith("/objects/shopping_list/23")
    assert captured["json"] == {"note": "dringend [grocy_ai_mhd:2026-12-31]"}


def test_update_shopping_list_item_note_calls_put_endpoint(monkeypatch):
    captured = {}

    def fake_put(url, *args, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse({})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_shopping_list_item_note(
        23,
        "nur bei Angebot",
        current_best_before_date="2026-12-31",
    )

    assert captured["url"].endswith("/objects/shopping_list/23")
    assert captured["json"] == {"note": "nur bei Angebot [grocy_ai_mhd:2026-12-31]"}


def test_best_before_date_is_extracted_from_shopping_list_note(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/products"):
            return FakeResponse([{"id": 5, "name": "Milch"}])
        if url.endswith("/stock"):
            return FakeResponse([])
        raise AssertionError(f"Unexpected URL: {url}")

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

    result = client._enrich_shopping_items(
        [{"id": 1, "product_id": 5, "note": "Bio [grocy_ai_mhd:2027-01-01]"}]
    )

    assert result[0]["best_before_date"] == "2027-01-01"
    assert result[0]["note"] == "Bio"


def test_enrich_shopping_items_does_not_use_stock_best_before_date_without_note(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/products"):
            return FakeResponse([{"id": 5, "name": "Milch"}])
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 5,
                        "best_before_date": "2028-04-20",
                        "amount": "1",
                    }
                ]
            )
        raise AssertionError(f"Unexpected URL: {url}")

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

    result = client._enrich_shopping_items([{"id": 1, "product_id": 5, "note": ""}])

    assert result[0]["best_before_date"] == ""


def test_embed_best_before_date_in_note_replaces_existing_marker():
    result = GrocyClient._embed_best_before_date_in_note(
        "Alt [grocy_ai_mhd:2020-01-01]",
        "2030-12-31",
    )

    assert result == "Alt [grocy_ai_mhd:2030-12-31]"


def test_complete_shopping_list_item_adds_to_stock_and_removes_list_entry(monkeypatch):
    post_calls = []
    delete_calls = []

    def fake_post(url, *args, **kwargs):
        post_calls.append((url, kwargs.get("json")))
        return FakeResponse({})

    def fake_delete(url, *args, **kwargs):
        delete_calls.append(url)
        return FakeResponse({})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.post", fake_post
    )
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

    client.complete_shopping_list_item(
        9,
        product_id=5,
        amount="3",
        best_before_date="2026-12-31",
    )

    assert post_calls[0][0].endswith("/stock/products/5/add")
    assert post_calls[0][1] == {"amount": "3", "best_before_date": "2026-12-31"}
    assert delete_calls[0].endswith("/objects/shopping_list/9")


def test_find_product_by_barcode_uses_primary_endpoint(monkeypatch):
    class PrimaryHitResponse(FakeResponse):
        status_code = 200

    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock/products/by-barcode/4008400408400"):
            return PrimaryHitResponse({"product": {"id": 3, "name": "Nudeln"}})
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

    assert client.find_product_by_barcode("4008400408400") == {
        "id": 3,
        "name": "Nudeln",
    }


def test_find_product_by_barcode_falls_back_to_product_barcodes(monkeypatch):
    class NotFoundResponse(FakeResponse):
        status_code = 404

    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock/products/by-barcode/4008400408400"):
            return NotFoundResponse({})
        if url.endswith("/objects/product_barcodes"):
            assert kwargs.get("params") == {"query[]": "barcode=4008400408400"}
            return FakeResponse([{"product_id": 12, "barcode": "4008400408400"}])
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {"id": 11, "name": "Butter"},
                    {"id": 12, "name": "Vollkornbrot"},
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

    assert client.find_product_by_barcode("4008400408400") == {
        "id": 12,
        "name": "Vollkornbrot",
    }


def test_find_product_by_barcode_falls_back_on_primary_bad_request(monkeypatch):
    class BadRequestResponse(FakeResponse):
        status_code = 400

    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock/products/by-barcode/4008400408400"):
            return BadRequestResponse({"error": "invalid barcode format"})
        if url.endswith("/objects/product_barcodes"):
            assert kwargs.get("params") == {"query[]": "barcode=4008400408400"}
            return FakeResponse([{"product_id": 12, "barcode": "4008400408400"}])
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {"id": 11, "name": "Butter"},
                    {"id": 12, "name": "Vollkornbrot"},
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

    assert client.find_product_by_barcode("4008400408400") == {
        "id": 12,
        "name": "Vollkornbrot",
    }


def test_get_recipe_ingredients_includes_unit_attribution(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/recipes_pos"):
            return FakeResponse(
                [
                    {"recipe_id": 10, "product_id": 1, "amount": "2", "qu_id": 5},
                    {"recipe_id": 10, "product_id": 2, "amount": "150"},
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {"id": 1, "name": "Ei", "qu_id_stock": 5},
                    {"id": 2, "name": "Mehl", "qu_id_stock": 6},
                ]
            )
        if url.endswith("/objects/quantity_units"):
            return FakeResponse(
                [
                    {"id": 5, "name": "Stk."},
                    {"id": 6, "name": "Gramm"},
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

    assert client.get_recipe_ingredients(10) == ["2 Stk. Ei", "150 Gramm Mehl"]


def test_get_stock_products_includes_nutrition_values(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "id": 77,
                        "product_id": 10,
                        "location_id": 1,
                        "amount": 2,
                        "best_before_date": "2026-01-01",
                    }
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse(
                [
                    {
                        "id": 10,
                        "name": "Milch",
                        "calories": 120,
                        "carbohydrates": 4.5,
                        "fat": 3.2,
                        "protein": 8,
                        "sugar": 4,
                    }
                ]
            )
        if url.endswith("/objects/locations"):
            return FakeResponse([{"id": 1, "name": "Keller"}])
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
    assert result[0]["calories"] == "120"
    assert result[0]["carbs"] == "4.5"
    assert result[0]["fat"] == "3.2"
    assert result[0]["protein"] == "8"
    assert result[0]["sugar"] == "4"



def test_get_stock_products_returns_stock_id(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "id": 77,
                        "product_id": 10,
                        "location_id": 1,
                        "amount": 2,
                        "best_before_date": "2026-01-01",
                    }
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse([{"id": 10, "name": "Milch"}])
        if url.endswith("/objects/locations"):
            return FakeResponse([{"id": 1, "name": "Keller"}])
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
    assert result[0]["stock_id"] == 77


def test_get_stock_products_falls_back_to_objects_stock_ids(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/stock"):
            return FakeResponse(
                [
                    {
                        "id": 88,
                        "product_id": 10,
                        "location_id": 1,
                        "amount": "2",
                        "best_before_date": "2026-01-01",
                    }
                ]
            )
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 10,
                        "location_id": 1,
                        "amount": "2",
                        "best_before_date": "2026-01-01",
                    }
                ]
            )
        if url.endswith("/objects/products"):
            return FakeResponse([{"id": 10, "name": "Milch"}])
        if url.endswith("/objects/locations"):
            return FakeResponse([{"id": 1, "name": "Keller"}])
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
    assert result[0]["stock_id"] == 88


def test_get_stock_entries_falls_back_to_objects_stock_ids(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/stock"):
            return FakeResponse(
                [
                    {
                        "id": 91,
                        "product_id": 10,
                        "location_id": 1,
                        "amount": "2",
                        "best_before_date": "2026-01-01",
                    }
                ]
            )
        if url.endswith("/stock"):
            return FakeResponse(
                [
                    {
                        "product_id": 10,
                        "location_id": 1,
                        "amount": "2",
                        "best_before_date": "2026-01-01",
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

    result = client.get_stock_entries()
    assert result[0]["stock_id"] == 91


def test_consume_stock_product_uses_product_and_stock_id(monkeypatch):
    called = {}

    class FakePostResponse(FakeResponse):
        pass

    def fake_post(url, *args, **kwargs):
        called["url"] = url
        called["json"] = kwargs.get("json")
        return FakePostResponse({})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.post", fake_post
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.consume_stock_product(product_id=10, amount=1.5, stock_id=77)

    assert called["url"].endswith("/stock/products/10/consume")
    assert called["json"] == {"amount": 1.5, "stock_entry_id": 77}






def test_resolve_stock_entry_id_for_product_prefers_location_match(monkeypatch):
    def fake_get(url, headers, timeout, params=None):
        if url.endswith('/objects/stock'):
            return FakeResponse(
                [
                    {"id": 11, "product_id": 42, "location_id": 1},
                    {"id": 12, "product_id": 42, "location_id": 2},
                ]
            )
        raise AssertionError(f"Unexpected URL: {url}")

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

    assert client.resolve_stock_entry_id_for_product(product_id=42, location_id=2) == 12
    assert client.resolve_stock_entry_id_for_product(product_id=42, location_id=999) == 11
    assert client.resolve_stock_entry_id_for_product(product_id=999, location_id=2) is None
def test_add_product_to_stock_posts_stock_add(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse({"ok": True})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.post", fake_post
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.add_product_to_stock(product_id=42, amount=3.5, best_before_date="2026-01-31")

    assert captured["url"].endswith("/stock/products/42/add")
    assert captured["json"] == {"amount": 3.5, "best_before_date": "2026-01-31"}
def test_update_stock_entry_updates_amount_and_best_before(monkeypatch):
    called = {}

    class FakePutResponse(FakeResponse):
        pass

    def fake_put(url, *args, **kwargs):
        called["url"] = url
        called["json"] = kwargs.get("json")
        return FakePutResponse({})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_stock_entry(stock_id=77, amount=3, best_before_date="2026-01-31")

    assert called["url"].endswith("/objects/stock/77")
    assert called["json"] == {"amount": 3, "best_before_date": "2026-01-31"}


def test_update_stock_entry_omits_empty_best_before_date(monkeypatch):
    called = {}

    class FakePutResponse(FakeResponse):
        pass

    def fake_put(url, *args, **kwargs):
        called["url"] = url
        called["json"] = kwargs.get("json")
        return FakePutResponse({})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_stock_entry(stock_id=77, amount=3, best_before_date="")

    assert called["url"].endswith("/objects/stock/77")
    assert called["json"] == {"amount": 3}


def test_delete_stock_entry_deletes_objects_stock(monkeypatch):
    called = {}

    class FakeDeleteResponse(FakeResponse):
        pass

    def fake_delete(url, *args, **kwargs):
        called["url"] = url
        return FakeDeleteResponse({})

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

    client.delete_stock_entry(stock_id=77)

    assert called["url"].endswith("/objects/stock/77")


def test_update_product_nutrition_updates_product_object(monkeypatch):
    captured = {}

    def fake_put(url, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse({"ok": True})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_product_nutrition(
        product_id=42,
        calories=123,
        carbs=4.5,
        fat=6,
        protein=7,
        sugar=8,
    )

    assert captured["url"].endswith("/objects/products/42")
    assert captured["json"] == {
        "calories": 123,
        "carbohydrates": 4.5,
        "fat": 6,
        "protein": 7,
        "sugar": 8,
    }


def test_update_product_nutrition_retries_without_unknown_columns(monkeypatch):
    calls = []

    class BadRequestResponse:
        def __init__(self, text):
            self.status_code = 400
            self.text = text

        def raise_for_status(self):
            raise HTTPError("Bad Request")

    class SuccessResponse:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

    def fake_put(url, headers, json, timeout):
        calls.append(json)
        if len(calls) == 1:
            return BadRequestResponse(
                '{"error_message":"table products has no column named calories"}'
            )
        if len(calls) == 2:
            return BadRequestResponse(
                '{"error_message":"table products has no column named carbohydrates"}'
            )
        return SuccessResponse()

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_product_nutrition(product_id=42, calories=123, carbs=4.5)

    assert calls[0] == {
        "calories": 123,
        "carbohydrates": 4.5,
    }
    assert calls[1] == {"carbohydrates": 4.5}


def test_update_product_nutrition_skips_when_no_values():
    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_product_nutrition(product_id=42)


def test_update_product_nutrition_skips_on_non_unknown_400(monkeypatch):
    calls = []

    class BadRequestResponse:
        status_code = 400
        text = '{"error_message":"invalid payload"}'

        def raise_for_status(self):
            raise HTTPError("Bad Request")

    def fake_put(url, headers, json, timeout):
        calls.append(json)
        return BadRequestResponse()

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.update_product_nutrition(product_id=42, calories=123)

    assert calls == [{"calories": 123}]


def test_clear_product_picture_sets_picture_file_name_to_none(monkeypatch):
    called = {}

    class FakePutResponse(FakeResponse):
        pass

    def fake_put(url, *args, **kwargs):
        called["url"] = url
        called["json"] = kwargs.get("json")
        return FakePutResponse({})

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    client.clear_product_picture(product_id=42)

    assert called["url"].endswith("/objects/products/42")
    assert called["json"] == {"picture_file_name": None}


def test_attach_product_picture_uploads_file_and_updates_product(monkeypatch, tmp_path):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_request(method, url, headers=None, data=None, json=None, timeout=None):
        calls.append((method, url, headers, data, json))
        return FakeResponse()

    def fake_put(url, headers=None, data=None, json=None, timeout=None):
        calls.append(("PUT", url, headers, data, json))
        return FakeResponse()

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.request", fake_request
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    image_path = tmp_path / "my_product.png"
    image_path.write_bytes(b"img")

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            grocy_base_url="http://grocy.local/api",
        )
    )

    result = client.attach_product_picture(10, str(image_path))

    assert result == "my_product.png"
    assert calls[0][0] == "PUT"
    assert calls[0][1] == "http://grocy.local/api/files/productpictures/my_product.png"
    assert calls[0][2]["Accept"] == "*/*"
    assert calls[0][2]["GROCY-API-KEY"] == "g"
    assert calls[0][3] == b"img"
    assert calls[1][1] == "http://grocy.local/api/objects/products/10"
    assert calls[1][4] == {"picture_file_name": "my_product.png"}


def test_attach_product_picture_retries_without_api_key_headers_on_405(
    monkeypatch, tmp_path
):
    calls = []

    class FakeResponse:
        def __init__(self, status_code=200):
            self.status_code = status_code

        def __bool__(self):
            return self.status_code < 400

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"{self.status_code} error")
                error.response = self
                raise error

    def fake_request(method, url, headers=None, data=None, json=None, timeout=None):
        calls.append((method, url, headers, data, json))
        if (
            headers
            and headers.get("GROCY-API-KEY")
            and "/files/productpictures/" in url
        ):
            return FakeResponse(status_code=405)
        return FakeResponse(status_code=200)

    def fake_put(url, headers=None, data=None, json=None, timeout=None):
        calls.append(("PUT", url, headers, data, json))
        return FakeResponse(status_code=200)

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.request", fake_request
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    image_path = tmp_path / "my_product.png"
    image_path.write_bytes(b"img")

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            grocy_base_url="http://grocy.local/api",
        )
    )

    result = client.attach_product_picture(10, str(image_path))

    assert result == "my_product.png"
    assert calls[0][1] == "http://grocy.local/api/files/productpictures/my_product.png"
    assert calls[0][2]["GROCY-API-KEY"] == "g"
    assert calls[1][1] == "http://grocy.local/api/files/productpictures/my_product.png"
    assert "GROCY-API-KEY" not in calls[1][2]
    assert calls[2][1] == "http://grocy.local/api/objects/products/10"


def test_attach_product_picture_retries_without_api_prefix_on_405(
    monkeypatch, tmp_path
):
    calls = []

    class FakeResponse:
        def __init__(self, status_code=200):
            self.status_code = status_code

        def __bool__(self):
            return self.status_code < 400

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"{self.status_code} error")
                error.response = self
                raise error

    def fake_request(method, url, headers=None, data=None, json=None, timeout=None):
        calls.append((method, url, headers, data, json))
        if url.startswith("http://grocy.local/api/files/productpictures/"):
            return FakeResponse(status_code=405)
        if url.startswith("http://grocy.local/files/productpictures/") and headers.get(
            "GROCY-API-KEY"
        ):
            return FakeResponse(status_code=405)
        return FakeResponse(status_code=200)

    def fake_put(url, headers=None, data=None, json=None, timeout=None):
        calls.append(("PUT", url, headers, data, json))
        return FakeResponse(status_code=200)

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.request", fake_request
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    image_path = tmp_path / "my_product.png"
    image_path.write_bytes(b"img")

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            grocy_base_url="http://grocy.local/api",
        )
    )

    result = client.attach_product_picture(10, str(image_path))

    assert result == "my_product.png"
    upload_calls = [call for call in calls if "/files/productpictures/" in call[1]]
    assert (
        upload_calls[0][1]
        == "http://grocy.local/api/files/productpictures/my_product.png"
    )
    assert any(
        call[1] == "http://grocy.local/files/productpictures/my_product.png"
        and "GROCY-API-KEY" not in call[2]
        for call in upload_calls
    )
    assert calls[-1][1] == "http://grocy.local/api/objects/products/10"


def test_attach_product_picture_retries_with_post_on_put_405(monkeypatch, tmp_path):
    calls = []

    class FakeResponse:
        def __init__(self, status_code=200):
            self.status_code = status_code

        def __bool__(self):
            return self.status_code < 400

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"{self.status_code} error")
                error.response = self
                raise error

    def fake_request(method, url, headers=None, data=None, json=None, timeout=None):
        calls.append((method, url, headers, data, json))
        is_picture_upload = "/files/productpictures/" in url
        if is_picture_upload and method == "PUT":
            return FakeResponse(status_code=405)
        return FakeResponse(status_code=200)

    def fake_put(url, headers=None, data=None, json=None, timeout=None):
        calls.append(("PUT", url, headers, data, json))
        return FakeResponse(status_code=200)

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.request", fake_request
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    image_path = tmp_path / "my_product.png"
    image_path.write_bytes(b"img")

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            grocy_base_url="http://grocy.local/api",
        )
    )

    result = client.attach_product_picture(10, str(image_path))

    assert result == "my_product.png"
    assert calls[0][0] == "PUT"
    assert calls[1][0] == "PUT"
    assert calls[2][0] == "POST"
    assert calls[2][1] == "http://grocy.local/api/files/productpictures/my_product.png"
    assert calls[3][0] == "PUT"
    assert calls[3][1] == "http://grocy.local/api/objects/products/10"


def test_attach_product_picture_retries_with_base64_filename(monkeypatch, tmp_path):
    calls = []

    class FakeResponse:
        def __init__(self, status_code=200):
            self.status_code = status_code

        def __bool__(self):
            return self.status_code < 400

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"{self.status_code} error")
                error.response = self
                raise error

    image_path = tmp_path / "my_product.png"
    image_path.write_bytes(b"img")

    encoded_file_name = b64encode(image_path.name.encode("utf-8")).decode("ascii")

    def fake_request(method, url, headers=None, data=None, json=None, timeout=None):
        calls.append((method, url, headers, data, json))
        if url.endswith(f"/productpictures/{encoded_file_name}"):
            return FakeResponse(status_code=200)
        return FakeResponse(status_code=404)

    def fake_put(url, headers=None, data=None, json=None, timeout=None):
        calls.append(("PUT", url, headers, data, json))
        return FakeResponse(status_code=200)

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.request", fake_request
    )
    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            grocy_base_url="http://grocy.local/api",
        )
    )

    result = client.attach_product_picture(10, str(image_path))

    assert result == "my_product.png"
    upload_urls = [call[1] for call in calls if "/files/productpictures/" in call[1]]
    assert (
        f"http://grocy.local/api/files/productpictures/{encoded_file_name}"
        in upload_urls
    )
    assert calls[-1][1] == "http://grocy.local/api/objects/products/10"


def test_create_product_retries_with_sanitized_payload_on_400(monkeypatch):
    class BadRequestResponse:
        status_code = 400
        text = "invalid fields"

        def raise_for_status(self):
            raise HTTPError("Bad Request")

        def json(self):
            return {}

    class CreatedResponse:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {"created_object_id": 42}

    posted_payloads = []

    def fake_post(url, *args, **kwargs):
        posted_payloads.append(kwargs.get("json"))
        if len(posted_payloads) == 1:
            return BadRequestResponse()
        return CreatedResponse()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/locations"):
            return FakeResponse([{"id": 3, "name": "Speisekammer"}])
        if url.endswith("/objects/quantity_units"):
            return FakeResponse([{"id": 2, "name": "Packung"}])
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.post", fake_post
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

    created_id = client.create_product(
        {
            "name": "Oliven",
            "description": "text",
            "location_id": 999,
            "qu_id_purchase": 999,
            "qu_id_stock": 999,
            "calories": 160,
            "carbohydrates": 7,
        }
    )

    assert created_id == 42
    assert len(posted_payloads) == 2
    assert posted_payloads[1] == {
        "name": "Oliven",
        "description": "text",
        "location_id": 3,
        "qu_id_purchase": 2,
        "qu_id_stock": 2,
        "qu_factor_purchase_to_stock": 1,
    }


def test_create_product_keeps_valid_ids_in_retry_payload(monkeypatch):
    posted_payloads = []

    class BadRequestResponse:
        status_code = 400
        text = "invalid fields"

        def raise_for_status(self):
            raise HTTPError("Bad Request")

        def json(self):
            return {}

    class CreatedResponse:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {"created_object_id": 9}

    def fake_post(url, *args, **kwargs):
        posted_payloads.append(kwargs.get("json"))
        return BadRequestResponse() if len(posted_payloads) == 1 else CreatedResponse()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/locations"):
            return FakeResponse([{"id": 1, "name": "Kuehlschrank"}])
        if url.endswith("/objects/quantity_units"):
            return FakeResponse(
                [{"id": 1, "name": "Stueck"}, {"id": 2, "name": "Packung"}]
            )
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.post", fake_post
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

    client.create_product(
        {
            "name": "Oliven",
            "description": "text",
            "location_id": 1,
            "qu_id_purchase": 2,
            "qu_id_stock": 1,
            "fat": 14,
        }
    )

    assert posted_payloads[1]["location_id"] == 1
    assert posted_payloads[1]["qu_id_purchase"] == 2
    assert posted_payloads[1]["qu_id_stock"] == 1
    assert "fat" not in posted_payloads[1]


def test_create_product_retries_by_removing_unknown_columns(monkeypatch):
    posted_payloads = []

    class BadRequestResponse:
        def __init__(self, text):
            self.status_code = 400
            self.text = text

        def raise_for_status(self):
            raise HTTPError("Bad Request")

        def json(self):
            return {}

    class CreatedResponse:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {"created_object_id": 33}

    def fake_post(url, *args, **kwargs):
        posted_payloads.append(kwargs.get("json"))
        if len(posted_payloads) == 1:
            return BadRequestResponse(
                '{"error_message":"table products has no column named carbohydrates"}'
            )
        if len(posted_payloads) == 2:
            return BadRequestResponse(
                '{"error_message":"table products has no column named qu_factor_purchase_to_stock"}'
            )
        return CreatedResponse()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/locations"):
            return FakeResponse([{"id": 1, "name": "Kuehlschrank"}])
        if url.endswith("/objects/quantity_units"):
            return FakeResponse([{"id": 1, "name": "Stueck"}])
        raise AssertionError(f"Unexpected url: {url}")

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.post", fake_post
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

    created_id = client.create_product(
        {
            "name": "Oliven",
            "description": "text",
            "location_id": 1,
            "qu_id_purchase": 1,
            "qu_id_stock": 1,
            "carbohydrates": 7,
            "fat": 14,
        }
    )

    assert created_id == 33
    assert len(posted_payloads) == 3
    assert "carbohydrates" in posted_payloads[0]
    assert "qu_factor_purchase_to_stock" in posted_payloads[1]
    assert "qu_factor_purchase_to_stock" not in posted_payloads[2]


def test_set_product_default_best_before_days_updates_product(monkeypatch):
    captured = {}

    def fake_put(url, *args, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse([])

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            grocy_base_url="http://grocy.local/api",
        )
    )

    result = client.set_product_default_best_before_days(7, 5)

    assert result == 5
    assert captured["url"] == "http://grocy.local/api/objects/products/7"
    assert captured["json"] == {"default_best_before_days": 5}


def test_set_product_default_best_before_days_ignores_invalid_values():
    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    assert client.set_product_default_best_before_days(7, 0) is None
    assert client.set_product_default_best_before_days(7, None) is None


def test_set_product_default_best_before_days_ignores_unknown_column(monkeypatch):
    class BadRequestResponse:
        status_code = 400
        text = (
            '{"error_message":"table products has no column named '
            'default_best_before_days"}'
        )

        def raise_for_status(self):
            raise HTTPError("Bad Request")

    def fake_put(url, *args, **kwargs):
        return BadRequestResponse()

    monkeypatch.setattr(
        "grocy_ai_assistant.services.grocy_client.requests.put", fake_put
    )

    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
            grocy_base_url="http://grocy.local/api",
        )
    )

    assert client.set_product_default_best_before_days(7, 5) is None


def test_get_storage_products_filters_by_search_query(monkeypatch):
    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    monkeypatch.setattr(
        client,
        "get_stock_products",
        lambda location_ids=None: [
            {"id": 1, "name": "Milch", "location_name": "Kühlschrank", "amount": "1"},
            {"id": 2, "name": "Brot", "location_name": "Vorrat", "amount": "1"},
        ],
    )

    result = client.get_storage_products(search_query="kühl")

    assert len(result) == 1
    assert result[0]["name"] == "Milch"


def test_resolve_best_before_date_prefers_explicit_value():
    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )

    assert (
        client.resolve_best_before_date(
            product_id=1,
            best_before_date="2027-01-05",
            default_best_before_days=4,
        )
        == "2027-01-05"
    )


def test_resolve_best_before_date_uses_global_fallback_when_no_defaults_available(monkeypatch):
    client = GrocyClient(
        Settings(
            api_key="x",
            addon_version="a",
            required_integration_version="1",
            grocy_api_key="g",
        )
    )
    monkeypatch.setattr(client, "_get_product_default_best_before_days", lambda _pid: None)

    expected = (
        datetime.now().date() + timedelta(days=GrocyClient.FALLBACK_BEST_BEFORE_DAYS)
    ).isoformat()
    assert client.resolve_best_before_date(product_id=12) == expected


def test_resolve_best_before_date_uses_default_days_from_product(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/objects/products"):
            return FakeResponse([{"id": 12, "default_best_before_days": 5}])
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

    expected = (datetime.now().date() + timedelta(days=5)).isoformat()
    assert client.resolve_best_before_date(product_id=12) == expected
