from collections import Counter
from math import sqrt
from typing import Any, Dict, Optional

import requests

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
        dot_product = sum(left_vector[key] * right_vector[key] for key in shared_dimensions)
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

    def find_product_by_name(self, product_name: str) -> Optional[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/products",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        products = response.json()

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
