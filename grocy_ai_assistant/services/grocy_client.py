from collections import Counter
from math import sqrt
from typing import Any, Dict, Optional

import requests
from requests import HTTPError

from grocy_ai_assistant.config.settings import Settings


class GrocyClient:
    MIN_VECTOR_SIMILARITY = 0.55

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _normalize_name(value: str) -> str:
        return (value or "").strip().casefold()

    @staticmethod
    def _build_trigram_vector(value: str) -> Counter[str]:
        normalized = GrocyClient._normalize_name(value)
        if not normalized:
            return Counter()

        padded = f"  {normalized}  "
        return Counter(padded[index : index + 3] for index in range(len(padded) - 2))

    @classmethod
    def _cosine_similarity(cls, left: str, right: str) -> float:
        left_vector = cls._build_trigram_vector(left)
        right_vector = cls._build_trigram_vector(right)

        if not left_vector or not right_vector:
            return 0.0

        shared_dimensions = set(left_vector) & set(right_vector)
        dot_product = sum(
            left_vector[key] * right_vector[key] for key in shared_dimensions
        )
        left_norm = sqrt(sum(weight * weight for weight in left_vector.values()))
        right_norm = sqrt(sum(weight * weight for weight in right_vector.values()))

        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0

        return dot_product / (left_norm * right_norm)

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "GROCY-API-KEY": self.settings.grocy_api_key,
            "Content-Type": "application/json",
        }

    def _get_all_products(self) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/products",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def search_products_by_partial_name(self, query: str) -> list[Dict[str, Any]]:
        normalized_query = self._normalize_name(query)
        if not normalized_query:
            return []

        products = self._get_all_products()
        return [
            product
            for product in products
            if normalized_query in self._normalize_name(product.get("name", ""))
        ]

    def find_product_by_name(self, product_name: str) -> Optional[Dict[str, Any]]:
        products = self._get_all_products()

        normalized_name = self._normalize_name(product_name)
        for product in products:
            if self._normalize_name(product.get("name")) == normalized_name:
                return product

        best_match: Optional[Dict[str, Any]] = None
        best_similarity = 0.0

        for product in products:
            similarity = self._cosine_similarity(product_name, product.get("name", ""))
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = product

        if best_similarity >= self.MIN_VECTOR_SIMILARITY:
            return best_match

        return None

    def create_product(self, product_payload: Dict[str, Any]) -> int:
        response = requests.post(
            f"{self.settings.grocy_base_url}/objects/products",
            headers=self.headers,
            json=product_payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("created_object_id")

    def add_product_to_shopping_list(self, product_id: int, amount: int = 1) -> None:
        response = requests.post(
            f"{self.settings.grocy_base_url}/stock/shoppinglist/add-product",
            headers=self.headers,
            json={"product_id": product_id, "amount": amount},
            timeout=30,
        )
        response.raise_for_status()

    def get_shopping_list(self) -> list[Dict[str, Any]]:
        stock_endpoint = f"{self.settings.grocy_base_url}/stock/shoppinglist"
        response = requests.get(stock_endpoint, headers=self.headers, timeout=30)

        try:
            response.raise_for_status()
            return response.json()
        except HTTPError:
            status_code = response.status_code
            if status_code != 405:
                raise

        objects_endpoint = f"{self.settings.grocy_base_url}/objects/shopping_list"
        response = requests.get(objects_endpoint, headers=self.headers, timeout=30)
        response.raise_for_status()
        shopping_items = response.json()

        products_response = requests.get(
            f"{self.settings.grocy_base_url}/objects/products",
            headers=self.headers,
            timeout=30,
        )
        products_response.raise_for_status()
        products = {
            str(product.get("id")): product
            for product in products_response.json()
            if product.get("id")
        }

        return [
            {
                **item,
                "product_name": products.get(str(item.get("product_id")), {}).get(
                    "name", "Unbekanntes Produkt"
                ),
                "picture_url": products.get(str(item.get("product_id")), {}).get(
                    "picture_url",
                    products.get(str(item.get("product_id")), {}).get(
                        "picture_file_name", ""
                    ),
                ),
            }
            for item in shopping_items
        ]

    def get_locations(self) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/locations",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        locations = payload if isinstance(payload, list) else []
        return [
            {"id": int(location.get("id")), "name": str(location.get("name") or "")}
            for location in locations
            if location.get("id") is not None
        ]

    def get_stock_products(
        self, location_ids: list[int] | None = None
    ) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/stock",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        stock_entries = response.json()

        products = {
            int(product.get("id")): product
            for product in self._get_all_products()
            if product.get("id") is not None
        }

        locations = {
            int(location.get("id")): location.get("name", "")
            for location in self.get_locations()
            if location.get("id") is not None
        }

        allowed_locations = {int(location_id) for location_id in (location_ids or [])}

        result: list[Dict[str, Any]] = []
        for entry in stock_entries:
            product_id = entry.get("product_id")
            if product_id is None:
                continue

            product = products.get(int(product_id), {})
            location_id = product.get("location_id") or entry.get("location_id")
            location_name = locations.get(int(location_id), "") if location_id else ""

            normalized_location_id = (
                int(location_id) if location_id is not None else None
            )
            if allowed_locations and normalized_location_id not in allowed_locations:
                continue

            result.append(
                {
                    "id": int(product_id),
                    "name": product.get("name")
                    or entry.get("product_name")
                    or "Unbekanntes Produkt",
                    "location_id": normalized_location_id,
                    "location_name": location_name,
                    "amount": str(entry.get("amount") or ""),
                }
            )

        result.sort(key=lambda item: item["name"].casefold())
        return result

    def get_recipes(self) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/recipes",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def clear_shopping_list(self) -> int:
        items = self.get_shopping_list()
        removed_items = 0

        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue

            response = requests.delete(
                f"{self.settings.grocy_base_url}/objects/shopping_list/{item_id}",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            removed_items += 1

        return removed_items
