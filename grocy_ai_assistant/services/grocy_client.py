from typing import Any, Dict, Optional

import requests

from grocy_ai_assistant.config.settings import Settings


class GrocyClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _normalize_name(value: str) -> str:
        return (value or "").strip().casefold()

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
        return next(
            (p for p in products if self._normalize_name(p.get("name")) == self._normalize_name(product_name)),
            None,
        )

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
        response = requests.get(
            f"{self.settings.grocy_base_url}/stock/shoppinglist",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
