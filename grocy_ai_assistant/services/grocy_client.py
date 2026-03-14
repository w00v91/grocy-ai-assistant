from collections import Counter
from datetime import datetime
from math import sqrt
import re
from typing import Any, Dict, Optional
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse
from base64 import b64encode

import requests
from requests import HTTPError

from grocy_ai_assistant.config.settings import Settings


class GrocyClient:
    MIN_VECTOR_SIMILARITY = 0.55
    SHOPPING_LIST_MHD_NOTE_PREFIX = "[grocy_ai_mhd:"
    SHOPPING_LIST_MHD_NOTE_PATTERN = re.compile(r"\[grocy_ai_mhd:(\d{4}-\d{2}-\d{2})\]")

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

    @staticmethod
    def _shopping_item_sort_key(item: Dict[str, Any]) -> tuple[int, str, int]:
        created = str(item.get("row_created_timestamp") or item.get("created_at") or "")
        parsed = ""
        if created:
            try:
                parsed = datetime.fromisoformat(
                    created.replace("Z", "+00:00")
                ).isoformat()
            except ValueError:
                parsed = created

        item_id = item.get("id")
        if isinstance(item_id, (int, str)) and str(item_id).isdigit():
            safe_item_id = int(item_id)
        else:
            safe_item_id = -1
        has_timestamp = 1 if parsed else 0
        return has_timestamp, parsed, safe_item_id

    @staticmethod
    def _safe_str(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _safe_str(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value) if value.is_integer() else None

        text = str(value).strip()
        if not text:
            return None

        return int(text) if text.isdigit() else None

    def _build_grocy_file_url(self, folder: str, file_name: Any) -> str:
        normalized_file_name = self._safe_str(file_name)
        if not normalized_file_name:
            return ""

        if normalized_file_name.startswith(("http://", "https://", "/")):
            return normalized_file_name

        base_url = self.settings.grocy_base_url.rstrip("/")
        return f"{base_url}/files/{folder}/{normalized_file_name}"

    @staticmethod
    def _encode_recipe_picture_path(path: str) -> str:
        if "/recipepictures/" not in path:
            return path

        prefix, _, suffix = path.rpartition("/")
        if not suffix or "." not in suffix:
            return path

        encoded_picture_name = b64encode(suffix.encode("utf-8")).decode("ascii")
        return f"{prefix}/{encoded_picture_name}"

    @staticmethod
    def _ensure_recipe_query(query: str) -> str:
        params = dict(parse_qsl(query, keep_blank_values=True))
        params.setdefault("force_serve_as", "picture")
        return urlencode(params)

    def _build_recipe_picture_url(
        self, picture_url: Any, picture_file_name: Any
    ) -> str:
        raw_picture_url = self._safe_str(picture_url)

        if raw_picture_url:
            parsed_picture = urlparse(raw_picture_url)
            rewritten_path = self._encode_recipe_picture_path(parsed_picture.path)
            rewritten_query = parsed_picture.query
            if "/recipepictures/" in rewritten_path:
                rewritten_query = self._ensure_recipe_query(parsed_picture.query)

            return ParseResult(
                scheme=parsed_picture.scheme,
                netloc=parsed_picture.netloc,
                path=rewritten_path,
                params=parsed_picture.params,
                query=rewritten_query,
                fragment=parsed_picture.fragment,
            ).geturl()

        raw_picture_name = self._safe_str(picture_file_name)
        if not raw_picture_name:
            return ""

        encoded_picture_name = b64encode(raw_picture_name.encode("utf-8")).decode(
            "ascii"
        )
        base_recipe_url = self._build_grocy_file_url(
            "recipepictures", encoded_picture_name
        )
        separator = "&" if "?" in base_recipe_url else "?"
        return f"{base_recipe_url}{separator}force_serve_as=picture"

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

    def find_product_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        normalized_barcode = "".join(ch for ch in str(barcode or "") if ch.isdigit())
        if len(normalized_barcode) < 8:
            return None

        primary_response = requests.get(
            f"{self.settings.grocy_base_url}/stock/products/by-barcode/{normalized_barcode}",
            headers=self.headers,
            timeout=30,
        )
        if primary_response.status_code == 200:
            payload = primary_response.json()
            if isinstance(payload, dict):
                product = (
                    payload.get("product")
                    if isinstance(payload.get("product"), dict)
                    else payload
                )
                if product.get("id") is not None:
                    return product

        if primary_response.status_code not in (200, 400, 404):
            primary_response.raise_for_status()

        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/product_barcodes",
            headers=self.headers,
            params={"query[]": f"barcode={normalized_barcode}"},
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        matches = payload if isinstance(payload, list) else []
        if not matches:
            return None

        product_id = self._safe_int(matches[0].get("product_id"))
        if product_id is None:
            return None

        for product in self._get_all_products():
            if self._safe_int(product.get("id")) == product_id:
                return product

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

    def add_product_to_shopping_list(
        self,
        product_id: int,
        amount: float = 1,
        best_before_date: str = "",
    ) -> None:
        payload: Dict[str, Any] = {"product_id": product_id, "amount": amount}
        normalized_best_before_date = best_before_date.strip()
        if normalized_best_before_date:
            payload["best_before_date"] = normalized_best_before_date

        response = requests.post(
            f"{self.settings.grocy_base_url}/stock/shoppinglist/add-product",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

    def update_shopping_list_item_best_before_date(
        self,
        shopping_list_id: int,
        best_before_date: str,
        current_note: str = "",
    ) -> None:
        note_with_best_before_date = self._embed_best_before_date_in_note(
            current_note,
            best_before_date,
        )
        response = requests.put(
            f"{self.settings.grocy_base_url}/objects/shopping_list/{shopping_list_id}",
            headers=self.headers,
            json={"note": note_with_best_before_date},
            timeout=30,
        )
        response.raise_for_status()

    def update_shopping_list_item_note(
        self,
        shopping_list_id: int,
        note: str,
        current_best_before_date: str = "",
    ) -> None:
        note_with_best_before_date = self._embed_best_before_date_in_note(
            note,
            current_best_before_date,
        )
        response = requests.put(
            f"{self.settings.grocy_base_url}/objects/shopping_list/{shopping_list_id}",
            headers=self.headers,
            json={"note": note_with_best_before_date},
            timeout=30,
        )
        response.raise_for_status()

    @classmethod
    def _extract_best_before_date_from_note(cls, note: str) -> tuple[str, str]:
        safe_note = cls._safe_str(note)
        match = cls.SHOPPING_LIST_MHD_NOTE_PATTERN.search(safe_note)
        if not match:
            return safe_note, ""

        clean_note = cls.SHOPPING_LIST_MHD_NOTE_PATTERN.sub("", safe_note).strip()
        return clean_note, match.group(1)

    @classmethod
    def _embed_best_before_date_in_note(cls, note: str, best_before_date: str) -> str:
        clean_note, _ = cls._extract_best_before_date_from_note(note)
        normalized_best_before_date = cls._safe_str(best_before_date)
        if not normalized_best_before_date:
            return clean_note

        if clean_note:
            return (
                f"{clean_note} {cls.SHOPPING_LIST_MHD_NOTE_PREFIX}"
                f"{normalized_best_before_date}]"
            )
        return f"{cls.SHOPPING_LIST_MHD_NOTE_PREFIX}{normalized_best_before_date}]"

    def _enrich_shopping_items(
        self, shopping_items: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        products: Dict[str, Any] = {}
        stock_by_product_id: Dict[str, Any] = {}
        locations: Dict[str, Any] = {}

        try:
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
        except Exception:
            products = {}

        try:
            stock_response = requests.get(
                f"{self.settings.grocy_base_url}/stock",
                headers=self.headers,
                timeout=30,
            )
            stock_response.raise_for_status()
            stock_entries = stock_response.json()
            for entry in stock_entries:
                product_id = self._safe_str(entry.get("product_id"))
                if not product_id:
                    continue
                stock_by_product_id[product_id] = entry
        except Exception:
            stock_by_product_id = {}

        try:
            locations = {
                str(location.get("id")): location.get("name", "")
                for location in self.get_locations()
                if location.get("id") is not None
            }
        except Exception:
            locations = {}

        merged_items = []
        for item in shopping_items:
            product_id = self._safe_str(item.get("product_id"))
            product = products.get(product_id, {})
            stock_entry = stock_by_product_id.get(product_id, {})
            clean_note, best_before_date_from_note = (
                self._extract_best_before_date_from_note(item.get("note"))
            )
            location_id = self._safe_str(
                stock_entry.get("location_id") or product.get("location_id")
            )
            merged_items.append(
                {
                    **item,
                    "product_id": self._safe_int(product_id),
                    "product_name": item.get("product_name")
                    or product.get("name")
                    or "Unbekanntes Produkt",
                    "picture_url": item.get("picture_url")
                    or product.get("picture_url")
                    or product.get("picture_file_name")
                    or "",
                    "location_name": locations.get(location_id, ""),
                    "in_stock": str(stock_entry.get("amount") or ""),
                    "note": clean_note,
                    "best_before_date": best_before_date_from_note
                    or str(
                        stock_entry.get("best_before_date")
                        or stock_entry.get("best_before_date_calculated")
                        or ""
                    ),
                    "default_amount": str(
                        product.get("default_best_before_days") or ""
                    ),
                    "calories": str(product.get("calories") or ""),
                    "carbs": str(product.get("carbohydrates") or ""),
                    "fat": str(product.get("fat") or ""),
                    "protein": str(product.get("protein") or ""),
                }
            )

        return sorted(merged_items, key=self._shopping_item_sort_key, reverse=True)

    def get_shopping_list(self) -> list[Dict[str, Any]]:
        stock_endpoint = f"{self.settings.grocy_base_url}/stock/shoppinglist"
        response = requests.get(stock_endpoint, headers=self.headers, timeout=30)

        try:
            response.raise_for_status()
            stock_items = response.json()
            return self._enrich_shopping_items(stock_items)
        except HTTPError:
            status_code = response.status_code
            if status_code != 405:
                raise

        objects_endpoint = f"{self.settings.grocy_base_url}/objects/shopping_list"
        response = requests.get(objects_endpoint, headers=self.headers, timeout=30)
        response.raise_for_status()
        shopping_items = response.json()

        return self._enrich_shopping_items(shopping_items)

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

    def get_stock_entries(
        self, location_ids: list[int] | None = None
    ) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/stock",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        stock_entries = response.json()
        if not isinstance(stock_entries, list):
            return []

        allowed_locations = {int(location_id) for location_id in (location_ids or [])}
        if not allowed_locations:
            return stock_entries

        filtered_entries: list[Dict[str, Any]] = []
        for entry in stock_entries:
            location_id = self._safe_int(entry.get("location_id"))
            if location_id in allowed_locations:
                filtered_entries.append(entry)

        return filtered_entries

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
            product_id = self._safe_int(entry.get("product_id"))
            if product_id is None:
                continue

            product = products.get(product_id, {})
            stock_location_id = self._safe_int(entry.get("location_id"))
            product_location_id = self._safe_int(product.get("location_id"))
            normalized_location_id = stock_location_id or product_location_id
            location_name = (
                locations.get(normalized_location_id, "")
                if normalized_location_id is not None
                else ""
            )
            if allowed_locations and normalized_location_id not in allowed_locations:
                continue

            result.append(
                {
                    "id": product_id,
                    "name": product.get("name")
                    or entry.get("product_name")
                    or "Unbekanntes Produkt",
                    "location_id": normalized_location_id,
                    "location_name": location_name,
                    "amount": str(entry.get("amount") or ""),
                    "best_before_date": str(
                        entry.get("best_before_date")
                        or entry.get("best_before_date_calculated")
                        or ""
                    ),
                }
            )

        result.sort(key=lambda item: item["name"].casefold())
        return result

    def get_recipe_positions(self, recipe_id: int) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/recipes_pos",
            headers=self.headers,
            params={"query[]": f"recipe_id={int(recipe_id)}"},
            timeout=30,
        )
        response.raise_for_status()
        positions = response.json()
        return positions if isinstance(positions, list) else []

    def get_stock_amounts(self) -> Dict[int, float]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/stock",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        stock_entries = response.json()
        if not isinstance(stock_entries, list):
            return {}

        amounts: Dict[int, float] = {}
        for entry in stock_entries:
            if not isinstance(entry, dict):
                continue
            product_id = self._safe_int(entry.get("product_id"))
            if product_id is None:
                continue
            amount_raw = entry.get("amount")
            try:
                amount_value = float(str(amount_raw).replace(",", "."))
            except (TypeError, ValueError):
                amount_value = 0.0
            amounts[product_id] = amount_value
        return amounts

    def get_missing_recipe_products(self, recipe_id: int) -> list[Dict[str, Any]]:
        positions = self.get_recipe_positions(recipe_id)
        if not positions:
            return []

        all_products = {
            int(product.get("id")): product
            for product in self._get_all_products()
            if self._safe_int(product.get("id")) is not None
        }
        stock_amounts = self.get_stock_amounts()

        missing: list[Dict[str, Any]] = []
        for position in positions:
            if not isinstance(position, dict):
                continue
            product_id = self._safe_int(position.get("product_id"))
            if product_id is None:
                continue
            needed_raw = position.get("amount")
            try:
                needed_amount = float(str(needed_raw).replace(",", "."))
            except (TypeError, ValueError):
                needed_amount = 1.0
            available_amount = float(stock_amounts.get(product_id, 0.0))
            if available_amount >= needed_amount:
                continue

            product = all_products.get(product_id, {})
            missing.append(
                {
                    "id": product_id,
                    "name": product.get("name")
                    or position.get("product")
                    or "Unbekanntes Produkt",
                    "picture_url": self._build_grocy_file_url(
                        "productpictures", product.get("picture_file_name")
                    ),
                    "source": "grocy",
                }
            )

        unique_missing: list[Dict[str, Any]] = []
        seen_ids: set[int] = set()
        for item in missing:
            item_id = self._safe_int(item.get("id"))
            if item_id is None or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            unique_missing.append(item)

        return unique_missing

    def _get_quantity_unit_map(self) -> Dict[int, str]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/quantity_units",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        units = response.json()
        if not isinstance(units, list):
            return {}

        mapped_units: Dict[int, str] = {}
        for item in units:
            if not isinstance(item, dict):
                continue

            unit_id = self._safe_int(item.get("id"))
            if unit_id is None:
                continue

            unit_name = (
                self._safe_str(item.get("name"))
                or self._safe_str(item.get("name_plural"))
            )
            if unit_name:
                mapped_units[unit_id] = unit_name

        return mapped_units

    def get_recipe_ingredients(self, recipe_id: int) -> list[str]:
        positions = self.get_recipe_positions(recipe_id)
        if not positions:
            return []

        all_products = {
            int(product.get("id")): product
            for product in self._get_all_products()
            if self._safe_int(product.get("id")) is not None
        }
        quantity_units = self._get_quantity_unit_map()

        ingredients: list[str] = []
        for position in positions:
            if not isinstance(position, dict):
                continue

            product_id = self._safe_int(position.get("product_id"))
            product = all_products.get(product_id or -1, {})
            product_name = (
                product.get("name")
                or position.get("product")
                or "Unbekannte Zutat"
            )

            amount = self._safe_str(position.get("amount"))
            position_unit_id = self._safe_int(position.get("qu_id"))
            product_unit_id = self._safe_int(product.get("qu_id_stock"))
            unit_name = (
                quantity_units.get(position_unit_id or -1)
                or quantity_units.get(product_unit_id or -1)
                or self._safe_str(position.get("quantity_unit_name"))
                or self._safe_str(position.get("qu_name"))
            )

            if amount and unit_name:
                ingredient_line = f"{amount} {unit_name} {product_name}"
            elif amount:
                ingredient_line = f"{amount} {product_name}"
            elif unit_name:
                ingredient_line = f"{unit_name} {product_name}"
            else:
                ingredient_line = str(product_name)

            ingredients.append(ingredient_line.strip())

        return ingredients

    def get_recipes(self) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/recipes",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        recipes = response.json()
        if not isinstance(recipes, list):
            return []

        normalized_recipes: list[Dict[str, Any]] = []
        for recipe in recipes:
            if not isinstance(recipe, dict):
                continue

            picture_url = self._build_recipe_picture_url(
                recipe.get("picture_url"), recipe.get("picture_file_name")
            )
            normalized_recipes.append({**recipe, "picture_url": picture_url})

        return normalized_recipes

    def delete_shopping_list_item(
        self, shopping_list_id: int, amount: str = "1"
    ) -> None:
        response = requests.delete(
            f"{self.settings.grocy_base_url}/objects/shopping_list/{shopping_list_id}",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()

    def clear_shopping_list(self) -> int:
        items = self.get_shopping_list()
        removed_items = 0

        for item in items:
            item_id = self._safe_int(item.get("id"))
            if item_id is None:
                continue

            amount_value = self._safe_str(item.get("amount") or "1") or "1"
            self.delete_shopping_list_item(item_id, amount=amount_value)
            removed_items += 1

        return removed_items

    def complete_shopping_list_item(
        self,
        shopping_list_id: int,
        product_id: int,
        amount: str = "1",
        best_before_date: str = "",
    ) -> None:
        payload: Dict[str, Any] = {
            "amount": self._safe_str(amount) or "1",
        }
        normalized_best_before_date = self._safe_str(best_before_date)
        if normalized_best_before_date:
            payload["best_before_date"] = normalized_best_before_date
        response = requests.post(
            f"{self.settings.grocy_base_url}/stock/products/{product_id}/add",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        self.delete_shopping_list_item(shopping_list_id, amount=payload["amount"])

    def complete_shopping_list(self) -> int:
        items = self.get_shopping_list()
        completed_items = 0

        for item in items:
            item_id = self._safe_int(item.get("id"))
            if item_id is None:
                continue

            product_id = self._safe_int(item.get("product_id"))
            if product_id is None:
                continue

            amount_value = self._safe_str(item.get("amount") or "1") or "1"
            self.complete_shopping_list_item(
                item_id,
                product_id=product_id,
                amount=amount_value,
                best_before_date=self._safe_str(item.get("best_before_date")),
            )
            completed_items += 1

        return completed_items
