from collections import Counter
import logging
from datetime import datetime, timedelta
from math import sqrt
from pathlib import Path
import re
from typing import Any, Dict, Optional
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse
from base64 import b64encode

import requests
from requests import HTTPError

from grocy_ai_assistant.config.settings import Settings

logger = logging.getLogger(__name__)


class GrocyClient:
    FALLBACK_BEST_BEFORE_DAYS = 4
    MIN_VECTOR_SIMILARITY = 0.55
    SHOPPING_LIST_MHD_NOTE_PREFIX = "[grocy_ai_mhd:"
    SHOPPING_LIST_MHD_NOTE_PATTERN = re.compile(r"\[grocy_ai_mhd:(\d{4}-\d{2}-\d{2})\]")
    UNKNOWN_COLUMN_PATTERN = re.compile(r"has no column named ([a-zA-Z0-9_]+)")

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _normalize_name(value: str) -> str:
        return (value or "").strip().casefold()

    @classmethod
    def _name_match_candidates(cls, value: str) -> set[str]:
        normalized = cls._normalize_name(value)
        if not normalized:
            return set()

        candidates = {normalized}
        for suffix in ("nen", "en", "ern", "er", "e", "n", "s"):
            if normalized.endswith(suffix):
                stem = normalized[: -len(suffix)]
                if len(stem) >= 4:
                    candidates.add(stem)

        return {candidate for candidate in candidates if len(candidate) >= 2}

    @classmethod
    def _is_fuzzy_partial_name_match(cls, query: str, product_name: str) -> bool:
        query_candidates = cls._name_match_candidates(query)
        product_candidates = cls._name_match_candidates(product_name)
        if not query_candidates or not product_candidates:
            return False

        return any(
            query_candidate in product_candidate or product_candidate in query_candidate
            for query_candidate in query_candidates
            for product_candidate in product_candidates
        )

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

    @classmethod
    def _is_compound_containment_match(cls, left: str, right: str) -> bool:
        normalized_left = cls._normalize_name(left)
        normalized_right = cls._normalize_name(right)
        if not normalized_left or not normalized_right:
            return False

        if normalized_left == normalized_right:
            return False

        if normalized_right.startswith(normalized_left):
            return len(normalized_right) - len(normalized_left) >= 2

        if normalized_left.startswith(normalized_right):
            return len(normalized_left) - len(normalized_right) >= 2

        return False

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

    @staticmethod
    def _to_string_or_empty(value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    @classmethod
    def _normalize_best_before_date(cls, best_before_date: Any) -> str:
        return cls._safe_str(best_before_date)

    def _get_product_default_best_before_days(self, product_id: int) -> int | None:
        for product in self._get_all_products():
            if self._safe_int(product.get("id")) != int(product_id):
                continue
            default_days = self._safe_int(product.get("default_best_before_days"))
            return default_days if default_days and default_days > 0 else None
        return None

    def get_product_default_best_before_days(self, product_id: int) -> int | None:
        return self._get_product_default_best_before_days(product_id)

    def set_product_default_best_before_days(
        self, product_id: int, default_best_before_days: Any
    ) -> int | None:
        days = self._safe_int(default_best_before_days)
        if days is None or days <= 0:
            return None

        response = requests.put(
            f"{self.settings.grocy_base_url}/objects/products/{int(product_id)}",
            headers=self.headers,
            json={"default_best_before_days": days},
            timeout=30,
        )
        try:
            response.raise_for_status()
        except HTTPError:
            if response.status_code != 400:
                raise

            sanitized_payload = self._remove_unknown_column_field(
                {"default_best_before_days": days},
                getattr(response, "text", ""),
            )
            if "default_best_before_days" not in sanitized_payload:
                return None
            raise
        return days

    def resolve_best_before_date(
        self,
        product_id: int,
        best_before_date: str = "",
        default_best_before_days: Any = None,
    ) -> str:
        normalized_best_before_date = self._normalize_best_before_date(best_before_date)
        if normalized_best_before_date:
            return normalized_best_before_date

        days = self._safe_int(default_best_before_days)
        if days is None or days <= 0:
            days = self._get_product_default_best_before_days(product_id)

        if days is None or days <= 0:
            days = self.FALLBACK_BEST_BEFORE_DAYS

        return (datetime.now().date() + timedelta(days=days)).isoformat()

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

    def get_products(self) -> list[Dict[str, Any]]:
        return self._get_all_products()

    def get_product_nutrition_map(
        self, product_ids: list[int] | set[int] | tuple[int, ...]
    ) -> dict[int, Dict[str, str]]:
        nutrition_map: dict[int, Dict[str, str]] = {}

        for product_id in {int(product_id) for product_id in product_ids if product_id}:
            nutrition_map[product_id] = {
                "carbs": "",
                "fat": "",
                "protein": "",
                "sugar": "",
            }

            try:
                response = requests.get(
                    f"{self.settings.grocy_base_url}/userfields/products/{product_id}",
                    headers=self.headers,
                    timeout=30,
                )
                response.raise_for_status()
            except HTTPError:
                if getattr(response, "status_code", None) not in {404, 405}:
                    raise
                continue
            except Exception:
                continue

            payload = response.json()
            userfields_payload = payload if isinstance(payload, dict) else {}
            nutrition_map[product_id] = {
                "carbs": str(userfields_payload.get("carbohydrates") or ""),
                "fat": str(userfields_payload.get("fat") or ""),
                "protein": str(userfields_payload.get("protein") or ""),
                "sugar": str(userfields_payload.get("sugar") or ""),
            }

        return nutrition_map

    def search_products_by_partial_name(self, query: str) -> list[Dict[str, Any]]:
        normalized_query = self._normalize_name(query)
        if not normalized_query:
            return []

        products = self._get_all_products()
        return [
            product
            for product in products
            if self._is_fuzzy_partial_name_match(query, product.get("name", ""))
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

        if best_similarity >= self.MIN_VECTOR_SIMILARITY and best_match:
            if self._is_compound_containment_match(
                product_name, best_match.get("name", "")
            ):
                return None
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

    def set_product_barcode(self, product_id: int, barcode: str) -> None:
        normalized_barcode = "".join(ch for ch in str(barcode or "") if ch.isdigit())
        if len(normalized_barcode) < 8:
            return

        response = requests.post(
            f"{self.settings.grocy_base_url}/objects/product_barcodes",
            headers=self.headers,
            json={
                "product_id": int(product_id),
                "barcode": normalized_barcode,
                "qu_id": 1,
                "amount": 1,
            },
            timeout=30,
        )
        response.raise_for_status()

    def get_products_without_picture(self) -> list[Dict[str, Any]]:
        products = self._get_all_products()
        return [
            product
            for product in products
            if not self._safe_str(product.get("picture_file_name"))
        ]

    def create_product(self, product_payload: Dict[str, Any]) -> int:
        create_endpoint = f"{self.settings.grocy_base_url}/objects/products"
        normalized_payload = self._normalize_product_payload_ids(product_payload)
        response = requests.post(
            create_endpoint,
            headers=self.headers,
            json=normalized_payload,
            timeout=30,
        )

        try:
            response.raise_for_status()
            return response.json().get("created_object_id")
        except HTTPError:
            if response.status_code != 400:
                raise

            retry_payload = self._build_product_payload_retry(
                normalized_payload,
                getattr(response, "text", ""),
            )
            if retry_payload == normalized_payload:
                raise

            attempted_payloads: list[Dict[str, Any]] = [normalized_payload]

            while retry_payload not in attempted_payloads:
                attempted_payloads.append(retry_payload)
                logger.warning(
                    "Grocy rejected product payload with 400. Retrying with sanitized payload. "
                    "response_body=%s",
                    response.text,
                )
                retry_response = requests.post(
                    create_endpoint,
                    headers=self.headers,
                    json=retry_payload,
                    timeout=30,
                )
                try:
                    retry_response.raise_for_status()
                    return retry_response.json().get("created_object_id")
                except HTTPError:
                    if retry_response.status_code != 400:
                        raise

                    next_payload = self._remove_unknown_column_field(
                        retry_payload,
                        retry_response.text,
                    )
                    if next_payload == retry_payload:
                        raise

                    response = retry_response
                    retry_payload = next_payload

            raise

    def _remove_unknown_column_field(
        self, product_payload: Dict[str, Any], response_text: str
    ) -> Dict[str, Any]:
        match = self.UNKNOWN_COLUMN_PATTERN.search(response_text or "")
        if not match:
            return product_payload

        unknown_field = match.group(1)
        if unknown_field not in product_payload:
            return product_payload

        return {
            key: value for key, value in product_payload.items() if key != unknown_field
        }

    def _normalize_product_payload_ids(
        self, product_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        valid_location_ids = {
            self._safe_int(item.get("id")) for item in self.get_locations()
        }
        valid_location_ids.discard(None)
        valid_unit_ids = {
            self._safe_int(unit_id) for unit_id in self.get_quantity_units().keys()
        }
        valid_unit_ids.discard(None)

        fallback_unit_id = next(iter(valid_unit_ids), 1)
        fallback_location_id = next(iter(valid_location_ids), 1)

        normalized_payload = dict(product_payload)

        location_id = self._safe_int(product_payload.get("location_id"))
        normalized_payload["location_id"] = (
            location_id if location_id in valid_location_ids else fallback_location_id
        )

        qu_id_stock = self._safe_int(product_payload.get("qu_id_stock"))
        normalized_payload["qu_id_stock"] = (
            qu_id_stock if qu_id_stock in valid_unit_ids else fallback_unit_id
        )

        qu_id_purchase = self._safe_int(product_payload.get("qu_id_purchase"))
        normalized_payload["qu_id_purchase"] = (
            qu_id_purchase
            if qu_id_purchase in valid_unit_ids
            else normalized_payload["qu_id_stock"]
        )

        return normalized_payload

    def _build_product_payload_retry(
        self, product_payload: Dict[str, Any], response_text: str
    ) -> Dict[str, Any]:
        if not self.UNKNOWN_COLUMN_PATTERN.search(response_text or ""):
            return product_payload

        normalized_payload = self._normalize_product_payload_ids(product_payload)

        return {
            "name": self._safe_str(normalized_payload.get("name")),
            "description": self._safe_str(normalized_payload.get("description")),
            "location_id": normalized_payload["location_id"],
            "qu_id_purchase": normalized_payload["qu_id_purchase"],
            "qu_id_stock": normalized_payload["qu_id_stock"],
            "qu_factor_purchase_to_stock": 1,
        }

    def attach_product_picture(self, product_id: int, image_path: str) -> str:
        file_name = Path(image_path).name
        encoded_file_name = b64encode(file_name.encode("utf-8")).decode("ascii")
        image_bytes = Path(image_path).read_bytes()

        upload_headers = {
            "GROCY-API-KEY": self.settings.grocy_api_key,
            "Content-Type": "application/octet-stream",
            "Accept": "*/*",
        }

        upload_url = f"{self.settings.grocy_base_url.rstrip('/')}/files/productpictures/{encoded_file_name}"
        upload_response = requests.put(
            upload_url,
            headers=upload_headers,
            data=image_bytes,
            timeout=60,
        )
        upload_response.raise_for_status()

        update_response = requests.put(
            f"{self.settings.grocy_base_url}/objects/products/{product_id}",
            headers=self.headers,
            json={"picture_file_name": file_name},
            timeout=30,
        )
        update_response.raise_for_status()
        return file_name

    def add_product_to_shopping_list(
        self,
        product_id: int,
        amount: float = 1,
        best_before_date: str = "",
    ) -> None:
        payload: Dict[str, Any] = {"product_id": product_id, "amount": amount}
        normalized_best_before_date = self._normalize_best_before_date(best_before_date)
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

    def update_shopping_list_item_amount(
        self,
        shopping_list_id: int,
        amount: str,
    ) -> None:
        response = requests.put(
            f"{self.settings.grocy_base_url}/objects/shopping_list/{shopping_list_id}",
            headers=self.headers,
            json={"amount": self._safe_str(amount) or "1"},
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

        nutrition_map = self.get_product_nutrition_map(
            [
                int(product_id)
                for product_id in (
                    self._safe_int(item.get("product_id")) for item in shopping_items
                )
                if product_id is not None
            ]
        )

        merged_items = []
        for item in shopping_items:
            product_id = self._safe_str(item.get("product_id"))
            nutrition = nutrition_map.get(self._safe_int(product_id) or 0, {})
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
                    "in_stock": self._to_string_or_empty(stock_entry.get("amount")),
                    "note": clean_note,
                    "best_before_date": best_before_date_from_note,
                    "default_amount": str(
                        product.get("default_best_before_days") or ""
                    ),
                    "calories": str(product.get("calories") or ""),
                    "carbs": str(nutrition.get("carbs") or ""),
                    "fat": str(nutrition.get("fat") or ""),
                    "protein": str(nutrition.get("protein") or ""),
                    "sugar": str(nutrition.get("sugar") or ""),
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
        stock_entries = self._merge_missing_stock_ids(self._get_stock_payload())
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

    def _get_stock_payload(self) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/stock",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def _get_stock_object_entries(self) -> list[Dict[str, Any]]:
        response = requests.get(
            f"{self.settings.grocy_base_url}/objects/stock",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def _normalize_stock_match_key(self, entry: Dict[str, Any]) -> tuple[Any, ...]:
        product_id = self._safe_int(entry.get("product_id"))
        location_id = self._safe_int(entry.get("location_id"))

        amount_raw = entry.get("amount")
        try:
            amount = float(str(amount_raw).replace(",", "."))
        except (TypeError, ValueError):
            amount = None

        best_before = self._safe_str(
            entry.get("best_before_date") or entry.get("best_before_date_calculated")
        )
        return product_id, location_id, amount, best_before

    def _merge_missing_stock_ids(
        self, stock_entries: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        if not stock_entries:
            return stock_entries

        if all(
            self._safe_int(entry.get("stock_id") or entry.get("id"))
            for entry in stock_entries
        ):
            return stock_entries

        stock_objects = self._get_stock_object_entries()
        if not stock_objects:
            return stock_entries

        ids_by_key: dict[tuple[Any, ...], list[int]] = {}
        for stock_object in stock_objects:
            stock_id = self._safe_int(stock_object.get("id"))
            if stock_id is None:
                continue
            key = self._normalize_stock_match_key(stock_object)
            ids_by_key.setdefault(key, []).append(stock_id)

        result: list[Dict[str, Any]] = []
        for entry in stock_entries:
            merged_entry = dict(entry)
            stock_id = self._safe_int(
                merged_entry.get("stock_id") or merged_entry.get("id")
            )
            if stock_id is None:
                key = self._normalize_stock_match_key(merged_entry)
                candidates = ids_by_key.get(key, [])
                if candidates:
                    merged_entry["stock_id"] = candidates.pop(0)
            result.append(merged_entry)

        return result

    def get_stock_products(
        self, location_ids: list[int] | None = None
    ) -> list[Dict[str, Any]]:
        stock_entries = self._merge_missing_stock_ids(self._get_stock_payload())

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

            item = {
                "id": product_id,
                "name": product.get("name")
                or entry.get("product_name")
                or "Unbekanntes Produkt",
                "in_stock": True,
                "picture_url": str(
                    product.get("picture_url") or product.get("picture_file_name") or ""
                ),
                "location_id": normalized_location_id,
                "location_name": location_name,
                "amount": self._to_string_or_empty(entry.get("amount")),
                "best_before_date": str(
                    entry.get("best_before_date")
                    or entry.get("best_before_date_calculated")
                    or ""
                ),
                "calories": str(product.get("calories") or ""),
                "carbs": str(product.get("carbohydrates") or ""),
                "fat": str(product.get("fat") or ""),
                "protein": str(product.get("protein") or ""),
                "sugar": str(product.get("sugar") or ""),
            }
            stock_id = self._safe_int(entry.get("stock_id") or entry.get("id"))
            if stock_id is not None:
                item["stock_id"] = stock_id
            result.append(item)

        result.sort(key=lambda item: item["name"].casefold())
        return result

    def get_storage_products(
        self,
        location_ids: list[int] | None = None,
        include_all_products: bool = False,
        search_query: str = "",
    ) -> list[Dict[str, Any]]:
        stock_products = (
            self.get_stock_products(location_ids)
            if location_ids
            else self.get_stock_products()
        )
        if include_all_products:
            allowed_locations = {
                int(location_id) for location_id in (location_ids or [])
            }
            product_ids_in_stock = {
                self._safe_int(item.get("id"))
                for item in stock_products
                if item.get("id") is not None
            }
            product_ids_in_stock.discard(None)

            locations = {
                int(location.get("id")): location.get("name", "")
                for location in self.get_locations()
                if location.get("id") is not None
            }

            for product in self._get_all_products():
                product_id = self._safe_int(product.get("id"))
                if product_id is None or product_id in product_ids_in_stock:
                    continue

                location_id = self._safe_int(product.get("location_id"))
                if allowed_locations and location_id not in allowed_locations:
                    continue

                stock_products.append(
                    {
                        "id": product_id,
                        "stock_id": None,
                        "in_stock": False,
                        "name": product.get("name") or "Unbekanntes Produkt",
                        "picture_url": str(
                            product.get("picture_url")
                            or product.get("picture_file_name")
                            or ""
                        ),
                        "location_id": location_id,
                        "location_name": (
                            locations.get(location_id, "")
                            if location_id is not None
                            else ""
                        ),
                        "amount": "0",
                        "best_before_date": "",
                        "calories": str(product.get("calories") or ""),
                        "carbs": str(product.get("carbohydrates") or ""),
                        "fat": str(product.get("fat") or ""),
                        "protein": str(product.get("protein") or ""),
                        "sugar": str(product.get("sugar") or ""),
                    }
                )

        filtered_products = stock_products
        normalized_query = search_query.strip().casefold()
        if normalized_query:
            filtered_products = [
                item
                for item in stock_products
                if normalized_query
                in f"{item.get('name', '')} {item.get('location_name', '')}".casefold()
            ]

        filtered_products.sort(key=lambda item: str(item.get("name") or "").casefold())
        return filtered_products

    def consume_stock_product(
        self,
        product_id: int,
        amount: float = 1,
        stock_id: int | None = None,
    ) -> None:
        payload: Dict[str, Any] = {"amount": amount}
        if stock_id is not None:
            payload["stock_entry_id"] = int(stock_id)

        response = requests.post(
            f"{self.settings.grocy_base_url}/stock/products/{int(product_id)}/consume",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

    def add_product_to_stock(
        self,
        product_id: int,
        amount: float,
        best_before_date: str = "",
    ) -> None:
        payload: Dict[str, Any] = {"amount": amount}
        normalized_best_before = str(best_before_date or "").strip()
        if normalized_best_before:
            payload["best_before_date"] = normalized_best_before

        response = requests.post(
            f"{self.settings.grocy_base_url}/stock/products/{int(product_id)}/add",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

    def resolve_stock_entry_id_for_product(
        self,
        product_id: int,
        location_id: int | None = None,
    ) -> int | None:
        stock_objects = self._get_stock_object_entries()
        product_matches = [
            entry
            for entry in stock_objects
            if self._safe_int(entry.get("product_id")) == int(product_id)
        ]
        if location_id is not None:
            location_matches = [
                entry
                for entry in product_matches
                if self._safe_int(entry.get("location_id")) == int(location_id)
            ]
            if location_matches:
                product_matches = location_matches

        for entry in product_matches:
            stock_id = self._safe_int(entry.get("id"))
            if stock_id is not None and stock_id > 0:
                return stock_id
        return None

    def update_stock_entry(
        self,
        stock_id: int,
        amount: float,
        best_before_date: str = "",
        location_id: int | None = None,
    ) -> None:
        payload: Dict[str, Any] = {"amount": amount}
        normalized_best_before = str(best_before_date or "").strip()
        if normalized_best_before:
            payload["best_before_date"] = normalized_best_before
        if location_id is not None and int(location_id) > 0:
            payload["location_id"] = int(location_id)

        response = requests.put(
            f"{self.settings.grocy_base_url}/objects/stock/{int(stock_id)}",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

    def update_product_location(self, product_id: int, location_id: int) -> None:
        response = requests.put(
            f"{self.settings.grocy_base_url}/objects/products/{int(product_id)}",
            headers=self.headers,
            json={"location_id": int(location_id)},
            timeout=30,
        )
        response.raise_for_status()

    def delete_stock_entry(self, stock_id: int) -> None:
        response = requests.delete(
            f"{self.settings.grocy_base_url}/objects/stock/{int(stock_id)}",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()

    def set_product_inventory(
        self,
        product_id: int,
        amount: float,
        stock_id: int | None = None,
    ) -> None:
        payload: Dict[str, Any] = {"new_amount": amount}
        if stock_id is not None:
            payload["stock_entry_id"] = int(stock_id)

        endpoint = (
            f"{self.settings.grocy_base_url}/stock/products/{int(product_id)}/inventory"
        )
        response = requests.post(
            endpoint,
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        try:
            response.raise_for_status()
        except HTTPError:
            if response.status_code != 400 or "stock_entry_id" not in payload:
                raise

            retry_payload = {"new_amount": amount}
            retry_response = requests.post(
                endpoint,
                headers=self.headers,
                json=retry_payload,
                timeout=30,
            )
            retry_response.raise_for_status()

    def delete_product(self, product_id: int) -> None:
        response = requests.delete(
            f"{self.settings.grocy_base_url}/objects/products/{int(product_id)}",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()

    def update_product_nutrition(
        self,
        product_id: int,
        calories: float | None = None,
        carbs: float | None = None,
        fat: float | None = None,
        protein: float | None = None,
        sugar: float | None = None,
    ) -> None:
        userfield_payload = {
            "carbohydrates": carbs,
            "fat": fat,
            "protein": protein,
            "sugar": sugar,
        }

        userfield_payload = {
            key: value for key, value in userfield_payload.items() if value is not None
        }

        if calories is not None:
            endpoint = (
                f"{self.settings.grocy_base_url}/objects/products/{int(product_id)}"
            )
            response = requests.put(
                endpoint,
                headers=self.headers,
                json={"calories": calories},
                timeout=30,
            )
            try:
                response.raise_for_status()
            except HTTPError:
                if response.status_code != 400:
                    raise

                logger.warning(
                    "Grocy rejected calories payload with 400. "
                    "Skipping calories update to avoid failing the request. response_body=%s",
                    response.text,
                )

        self._update_product_nutrition_userfields(product_id, userfield_payload)

    def get_product_nutrition(self, product_id: int) -> Dict[str, str]:
        product_response = requests.get(
            f"{self.settings.grocy_base_url}/objects/products/{int(product_id)}",
            headers=self.headers,
            timeout=30,
        )
        product_response.raise_for_status()
        product_payload = product_response.json()
        product = product_payload if isinstance(product_payload, dict) else {}

        userfields_response = requests.get(
            f"{self.settings.grocy_base_url}/userfields/products/{int(product_id)}",
            headers=self.headers,
            timeout=30,
        )
        userfields_payload: Dict[str, Any] = {}
        try:
            userfields_response.raise_for_status()
            raw_payload = userfields_response.json()
            userfields_payload = raw_payload if isinstance(raw_payload, dict) else {}
        except HTTPError:
            if getattr(userfields_response, "status_code", None) not in {404, 405}:
                raise

        return {
            "calories": str(product.get("calories") or ""),
            "carbs": str(userfields_payload.get("carbohydrates") or ""),
            "fat": str(userfields_payload.get("fat") or ""),
            "protein": str(userfields_payload.get("protein") or ""),
            "sugar": str(userfields_payload.get("sugar") or ""),
        }

    def _update_product_nutrition_userfields(
        self,
        product_id: int,
        userfield_payload: Dict[str, Any],
    ) -> None:
        if not userfield_payload:
            return

        endpoint = (
            f"{self.settings.grocy_base_url}/userfields/products/{int(product_id)}"
        )
        attempted_payloads: list[Dict[str, Any]] = []
        retry_payload = userfield_payload

        while retry_payload and retry_payload not in attempted_payloads:
            attempted_payloads.append(retry_payload)
            response = requests.put(
                endpoint,
                headers=self.headers,
                json=retry_payload,
                timeout=30,
            )
            try:
                response.raise_for_status()
                break
            except HTTPError:
                if response.status_code in {404, 405}:
                    logger.warning(
                        "Grocy userfields endpoint unavailable for product %s. "
                        "Skipping userfield nutrition sync. status=%s",
                        product_id,
                        response.status_code,
                    )
                    return

                if response.status_code != 400:
                    raise

                next_payload = self._remove_unknown_column_field(
                    retry_payload,
                    getattr(response, "text", ""),
                )
                if next_payload == retry_payload:
                    logger.warning(
                        "Grocy rejected userfield nutrition payload with 400 and no removable unknown column. "
                        "Skipping userfield nutrition update. response_body=%s",
                        response.text,
                    )
                    break

                logger.warning(
                    "Grocy rejected userfield nutrition payload with 400. Retrying without unknown column. "
                    "response_body=%s",
                    response.text,
                )
                retry_payload = next_payload

        if not retry_payload:
            logger.warning(
                "Userfield nutrition update skipped for product %s because target Grocy has no matching userfields.",
                product_id,
            )

        self._update_product_nutrition_userfields(product_id, userfield_payload)

    def _update_product_nutrition_userfields(
        self,
        product_id: int,
        userfield_payload: Dict[str, Any],
    ) -> None:
        if not userfield_payload:
            return

        endpoint = (
            f"{self.settings.grocy_base_url}/userfields/products/{int(product_id)}"
        )
        attempted_payloads: list[Dict[str, Any]] = []
        retry_payload = userfield_payload

        while retry_payload and retry_payload not in attempted_payloads:
            attempted_payloads.append(retry_payload)
            response = requests.put(
                endpoint,
                headers=self.headers,
                json=retry_payload,
                timeout=30,
            )
            try:
                response.raise_for_status()
                return
            except HTTPError:
                if response.status_code in {404, 405}:
                    logger.warning(
                        "Grocy userfields endpoint unavailable for product %s. "
                        "Skipping userfield nutrition sync. status=%s",
                        product_id,
                        response.status_code,
                    )
                    return

                if response.status_code != 400:
                    raise

                next_payload = self._remove_unknown_column_field(
                    retry_payload,
                    getattr(response, "text", ""),
                )
                if next_payload == retry_payload:
                    logger.warning(
                        "Grocy rejected userfield nutrition payload with 400 and no removable unknown column. "
                        "Skipping userfield nutrition update. response_body=%s",
                        response.text,
                    )
                    return

                logger.warning(
                    "Grocy rejected userfield nutrition payload with 400. Retrying without unknown column. "
                    "response_body=%s",
                    response.text,
                )
                retry_payload = next_payload

        if not retry_payload:
            logger.warning(
                "Userfield nutrition update skipped for product %s because target Grocy has no matching userfields.",
                product_id,
            )

    def clear_product_picture(self, product_id: int) -> None:
        response = requests.put(
            f"{self.settings.grocy_base_url}/objects/products/{int(product_id)}",
            headers=self.headers,
            json={"picture_file_name": None},
            timeout=30,
        )
        response.raise_for_status()

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

            unit_name = self._safe_str(item.get("name")) or self._safe_str(
                item.get("name_plural")
            )
            if unit_name:
                mapped_units[unit_id] = unit_name

        return mapped_units

    def get_quantity_units(self) -> Dict[int, str]:
        return self._get_quantity_unit_map()

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
                product.get("name") or position.get("product") or "Unbekannte Zutat"
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
        normalized_best_before_date = self._normalize_best_before_date(best_before_date)
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
