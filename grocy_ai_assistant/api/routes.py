import logging
import os
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult, quote, unquote, urlencode, urlparse, urlunparse
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from grocy_ai_assistant.ai.ingredient_detector import IngredientDetector
from grocy_ai_assistant.api.notification_store import (
    NotificationDashboardStore,
    create_history_entry,
)
from grocy_ai_assistant.api.errors import log_api_error
from grocy_ai_assistant.config.settings import Settings, get_settings
from grocy_ai_assistant.core.picture_urls import build_product_picture_url
from grocy_ai_assistant.core.text_utils import html_to_plain_text
from grocy_ai_assistant.models.ingredient import (
    AnalyzeProductRequest,
    AnalyzeProductResponse,
    BarcodeProductResponse,
    DashboardSearchResponse,
    ExistingProductAddRequest,
    LocationResponse,
    ProductVariantResponse,
    RecipeSuggestionItem,
    RecipeSuggestionRequest,
    RecipeSuggestionResponse,
    ShoppingListBestBeforeDateUpdateRequest,
    ShoppingListItemResponse,
    ShoppingListNoteUpdateRequest,
    ShoppingListAmountUpdateRequest,
    ScannerLlavaRequest,
    ScannerLlavaResponse,
    ScannerProductCreateRequest,
    StockProductConsumeRequest,
    StockProductResponse,
    StockProductUpdateRequest,
)
from grocy_ai_assistant.models.addon_api import (
    AddonCapabilitiesResponse,
    AddonCatalogRebuildResponse,
    AddonHealthResponse,
    AddonLastScanResponse,
    AddonStatusResponse,
)
from grocy_ai_assistant.models.notification import (
    NotificationDeviceUpdateRequest,
    NotificationOverviewResponse,
    NotificationRuleModel,
    NotificationRuleUpsertRequest,
    NotificationSettingsModel,
    NotificationSettingsUpdateRequest,
    NotificationTargetModel,
    NotificationTestRequest,
)
from grocy_ai_assistant.services.grocy_client import GrocyClient

logger = logging.getLogger(__name__)
GROCY_RECIPE_SUGGESTION_LIMIT = 3
AI_RECIPE_SUGGESTION_LIMIT = 3
AMOUNT_PREFIX_PATTERN = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s+(.+)$")
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
bearer_auth = HTTPBearer(auto_error=False)

NOTIFICATION_STORAGE_PATH = Path("/data/notification_dashboard.json")

LLAVA_REQUEST_LOCK = threading.Lock()
LLAVA_REQUEST_IN_FLIGHT = False
LLAVA_REQUEST_STARTED_AT = 0.0
LAST_SCAN_RESULT: dict[str, Any] = {
    "updated_at": "",
    "result": None,
}


def _call_homeassistant_service(
    domain: str,
    service: str,
    service_data: dict,
) -> tuple[bool, str | None, int | None]:
    supervisor_url = (os.getenv("SUPERVISOR_URL") or "http://supervisor").rstrip("/")
    endpoint_candidates: list[str] = []
    for endpoint in (
        f"{supervisor_url}/core/api/services/{domain}/{service}",
        f"{supervisor_url}/api/services/{domain}/{service}",
    ):
        if endpoint not in endpoint_candidates:
            endpoint_candidates.append(endpoint)

    header_candidates = _build_homeassistant_auth_headers()

    last_status_code: int | None = None
    errors: list[str] = []
    for endpoint in endpoint_candidates:
        for headers in header_candidates:
            try:
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=service_data,
                    timeout=10,
                )
            except requests.RequestException as err:
                errors.append(f"Home-Assistant-Service nicht erreichbar: {err}")
                continue

            last_status_code = response.status_code
            if response.status_code in {200, 201}:
                return True, None, response.status_code

            response_excerpt = (response.text or "").strip()
            if len(response_excerpt) > 180:
                response_excerpt = f"{response_excerpt[:180]}…"
            error_text = f"Service-Aufruf {domain}.{service} fehlgeschlagen ({response.status_code})"
            if response_excerpt:
                error_text = f"{error_text}: {response_excerpt}"
            errors.append(error_text)

    if not errors:
        errors.append(f"Service-Aufruf {domain}.{service} fehlgeschlagen")

    return False, " | ".join(errors), last_status_code


def _build_homeassistant_auth_headers() -> list[dict[str, str]]:
    token_candidates = [
        (os.getenv("SUPERVISOR_TOKEN") or "").strip(),
        (os.getenv("HASSIO_TOKEN") or "").strip(),
    ]
    unique_tokens: list[str] = []
    for token_candidate in token_candidates:
        if token_candidate and token_candidate not in unique_tokens:
            unique_tokens.append(token_candidate)

    header_candidates: list[dict[str, str]] = []
    for token in unique_tokens:
        header_candidates.extend(
            [
                {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                {
                    "Authorization": f"Bearer {token}",
                    "X-Supervisor-Token": token,
                    "Content-Type": "application/json",
                },
                {
                    "Authorization": f"Bearer {token}",
                    "X-Hassio-Key": token,
                    "Content-Type": "application/json",
                },
                {
                    "X-Supervisor-Token": token,
                    "Content-Type": "application/json",
                },
                {
                    "X-Hassio-Key": token,
                    "Content-Type": "application/json",
                },
            ]
        )

    header_candidates.append({"Content-Type": "application/json"})
    return header_candidates


def _build_persistent_notification_user_error(raw_error: str | None) -> str:
    error_text = (raw_error or "").lower()
    if "(401)" in error_text or "unauthorized" in error_text or "(403)" in error_text:
        return (
            "Persistente Benachrichtigung konnte nicht zugestellt werden: "
            "Home-Assistant-Autorisierung fehlgeschlagen (401/403). "
            "Bitte Add-on neu starten und Supervisor-/Home-Assistant-API-Berechtigungen prüfen."
        )
    if "(404)" in error_text or "service not found" in error_text:
        return (
            "Persistente Benachrichtigung konnte nicht zugestellt werden: "
            "Der benötigte Home-Assistant-Service wurde nicht gefunden."
        )
    if "nicht erreichbar" in error_text:
        return (
            "Persistente Benachrichtigung konnte nicht zugestellt werden: "
            "Home Assistant ist derzeit nicht erreichbar."
        )
    return "Persistente Benachrichtigung konnte nicht zugestellt werden. Bitte Add-on-Log prüfen."


def _send_persistent_notification_to_homeassistant(
    *,
    title: str,
    message: str,
    notification_id: str,
) -> tuple[bool, str | None]:
    service_data = {
        "title": title,
        "message": message,
        "notification_id": notification_id,
    }
    service_data_without_id = {
        "title": title,
        "message": message,
    }

    delivered, error, status_code = _call_homeassistant_service(
        "persistent_notification",
        "create",
        service_data,
    )
    if delivered:
        return True, None

    if status_code in {400, 422}:
        retry_delivered, retry_error, retry_status_code = _call_homeassistant_service(
            "persistent_notification",
            "create",
            service_data_without_id,
        )
        if retry_delivered:
            return True, None
        error = retry_error or error
        status_code = retry_status_code

    fallback_delivered, fallback_error, _ = _call_homeassistant_service(
        "notify",
        "persistent_notification",
        service_data_without_id,
    )
    if fallback_delivered:
        return True, None

    if status_code in {404, 405}:
        return False, fallback_error or error
    return False, error or fallback_error


def _build_mobile_notification_user_error(raw_error: str | None) -> str:
    error_text = (raw_error or "").lower()
    if "(401)" in error_text or "unauthorized" in error_text or "(403)" in error_text:
        return (
            "Mobile Benachrichtigung konnte nicht zugestellt werden: "
            "Home-Assistant-Autorisierung fehlgeschlagen (401/403). "
            "Bitte Add-on neu starten und Supervisor-/Home-Assistant-API-Berechtigungen prüfen."
        )
    if "(404)" in error_text or "service not found" in error_text:
        return (
            "Mobile Benachrichtigung konnte nicht zugestellt werden: "
            "Der gewählte Notify-Service wurde in Home Assistant nicht gefunden."
        )
    if "nicht erreichbar" in error_text:
        return (
            "Mobile Benachrichtigung konnte nicht zugestellt werden: "
            "Home Assistant ist derzeit nicht erreichbar."
        )
    return "Mobile Benachrichtigung konnte nicht zugestellt werden. Bitte Add-on-Log prüfen."


def _parse_csv_int_values(raw_value: str) -> list[int]:
    values: list[int] = []
    for chunk in str(raw_value or "").split(","):
        candidate = chunk.strip()
        if candidate.isdigit():
            values.append(int(candidate))
    return values


def _store_last_scan_result(result: ScannerLlavaResponse) -> None:
    LAST_SCAN_RESULT["updated_at"] = datetime.now(timezone.utc).isoformat()
    LAST_SCAN_RESULT["result"] = (
        result.model_dump() if hasattr(result, "model_dump") else result.dict()
    )


def _infer_mobile_platform(service_id: str, platform_hint: str = "") -> str:
    normalized_hint = (platform_hint or "").strip().lower()
    if normalized_hint in {"android", "ios"}:
        return normalized_hint

    service_name = (service_id or "").strip().lower()
    ios_markers = ("iphone", "ipad", "ios", "watch")
    if any(marker in service_name for marker in ios_markers):
        return "ios"
    return "android"


def _build_mobile_notification_payload(
    *,
    title: str,
    message: str,
    platform: str,
) -> dict:
    data = {
        "tag": "grocy-assistant",
        "group": "grocy-assistant",
        "icon": "mdi:fridge-outline",
        "notification_icon": "mdi:fridge-outline",
        "color": "#4F46E5",
    }

    payload = {
        "title": title,
        "message": message,
        "data": data,
    }

    if platform == "ios":
        payload["data"].update(
            {
                "url": "/lovelace/default_view",
                "push": {
                    "sound": "default",
                    "thread-id": "grocy-assistant",
                    "interruption-level": "active",
                },
            }
        )
    else:
        payload["data"].update(
            {
                "clickAction": "/lovelace/default_view",
                "channel": "Grocy Assistant",
                "ttl": 300,
                "priority": "high",
                "importance": "high",
                "sticky": False,
            }
        )

    return payload


def _send_mobile_notification_to_homeassistant(
    *,
    service_id: str,
    title: str,
    message: str,
    platform_hint: str = "",
) -> tuple[bool, str | None]:
    normalized_service = (service_id or "").strip()
    if not normalized_service.startswith("notify."):
        return False, "Ungültiger Notify-Service"

    service = normalized_service.split(".", 1)[1]
    if not service:
        return False, "Ungültiger Notify-Service"

    payload = _build_mobile_notification_payload(
        title=title,
        message=message,
        platform=_infer_mobile_platform(service_id, platform_hint),
    )
    delivered, error, _ = _call_homeassistant_service("notify", service, payload)
    return delivered, error


def _normalize_barcode_for_lookup(raw_barcode: str) -> str:
    digits_only = "".join(ch for ch in str(raw_barcode or "") if ch.isdigit())
    if not digits_only:
        return ""

    if len(digits_only) >= 16 and digits_only.startswith("01"):
        gtin14 = digits_only[2:16]
        if gtin14.startswith("0"):
            return gtin14[1:]
        return gtin14

    if len(digits_only) in (8, 12, 13, 14):
        return digits_only

    if len(digits_only) > 14:
        return digits_only[-13:]

    return digits_only


def _build_barcode_lookup_candidates(normalized_barcode: str) -> list[str]:
    candidates = [normalized_barcode]
    if len(normalized_barcode) == 12:
        candidates.append(f"0{normalized_barcode}")
    elif len(normalized_barcode) == 13 and normalized_barcode.startswith("0"):
        candidates.append(normalized_barcode[1:])

    unique_candidates: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def _try_openfoodfacts_lookup(
    barcode_candidates: list[str],
) -> tuple[str, dict[str, object]]:
    for candidate in barcode_candidates:
        response = requests.get(
            f"https://world.openfoodfacts.org/api/v2/product/{candidate}.json",
            timeout=8,
            headers={"User-Agent": "grocy-ai-assistant/scan-tab"},
        )
        payload = response.json()
        if response.status_code == 200 and int(payload.get("status", 0)) == 1:
            product = payload.get("product") if isinstance(payload, dict) else {}
            if isinstance(product, dict):
                return candidate, product

    return "", {}


def _acquire_llava_request_slot(timeout_seconds: int) -> bool:
    global LLAVA_REQUEST_IN_FLIGHT
    global LLAVA_REQUEST_STARTED_AT

    now = time.monotonic()
    with LLAVA_REQUEST_LOCK:
        if LLAVA_REQUEST_IN_FLIGHT:
            elapsed = now - LLAVA_REQUEST_STARTED_AT
            if elapsed < timeout_seconds:
                return False
        LLAVA_REQUEST_IN_FLIGHT = True
        LLAVA_REQUEST_STARTED_AT = now
        return True


def _release_llava_request_slot() -> None:
    global LLAVA_REQUEST_IN_FLIGHT

    with LLAVA_REQUEST_LOCK:
        LLAVA_REQUEST_IN_FLIGHT = False


def _build_product_picture_url(raw_picture_url: str, settings: Settings) -> str:
    rewritten = build_product_picture_url(raw_picture_url, settings)
    if rewritten and rewritten != (raw_picture_url or ""):
        logger.debug(
            "Produktbild-URL auf konfigurierten Grocy-Host umgeschrieben: %s -> %s",
            raw_picture_url,
            rewritten,
        )
    return rewritten


def _build_dashboard_picture_proxy_url(
    raw_picture_url: str, settings: Settings, *, size: str = "thumb"
) -> str:
    absolute_picture_url = _build_product_picture_url(raw_picture_url, settings)
    if not absolute_picture_url:
        return ""

    return (
        "/api/dashboard/product-picture"
        f"?src={quote(absolute_picture_url, safe='')}&size={quote(size, safe='')}"
    )


def _apply_picture_size(url: str, size: str) -> str:
    normalized_size = str(size or "thumb").strip().lower()
    dimensions_by_size = {
        "mobile": (64, 64),
        "thumb": (96, 96),
        "full": (720, 720),
    }
    if normalized_size not in dimensions_by_size:
        raise HTTPException(status_code=400, detail="Ungültige Bildgröße")

    width, height = dimensions_by_size[normalized_size]
    parsed = urlparse(url)
    query_values: dict[str, str] = {}
    if parsed.query:
        for query_item in parsed.query.split("&"):
            if not query_item:
                continue
            if "=" in query_item:
                key, value = query_item.split("=", 1)
            else:
                key, value = query_item, ""
            query_values[key] = value

    query_values["best_fit_width"] = str(width)
    query_values["best_fit_height"] = str(height)
    query_values.setdefault("force_serve_as", "picture")

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query_values),
            parsed.fragment,
        )
    )


def _normalize_dashboard_picture_source_url(src: str) -> str:
    parsed_src = urlparse(src)
    if parsed_src.query:
        return src

    decoded_path = unquote(parsed_src.path)
    if "?" not in decoded_path:
        return src

    normalized_path, normalized_query = decoded_path.split("?", 1)
    return ParseResult(
        scheme=parsed_src.scheme,
        netloc=parsed_src.netloc,
        path=normalized_path,
        params=parsed_src.params,
        query=normalized_query,
        fragment=parsed_src.fragment,
    ).geturl()


def _extract_shopping_item_picture_value(item: dict) -> str:
    product = item.get("product") if isinstance(item.get("product"), dict) else {}
    return (
        item.get("picture_url")
        or item.get("product_picture_url")
        or item.get("picture_file_name")
        or product.get("picture_url")
        or product.get("picture_file_name")
        or ""
    )


def _extract_amount_prefixed_product_input(raw_value: str) -> tuple[str, float | None]:
    value = raw_value.strip()
    match = AMOUNT_PREFIX_PATTERN.match(value)
    if not match:
        return value, None

    amount_raw, product_name = match.groups()
    try:
        parsed_amount = float(amount_raw.replace(",", "."))
    except ValueError:
        return value, None

    if parsed_amount <= 0:
        return value, None

    return product_name.strip(), parsed_amount


def _normalize_new_product_name(raw_name: str) -> str:
    compact_name = re.sub(r"\s+", " ", str(raw_name or "").strip())
    if not compact_name:
        return ""

    return f"{compact_name[:1].upper()}{compact_name[1:]}"


def _parse_float_or_none(value: object) -> float | None:
    normalized_value = str(value or "").strip().replace(",", ".")
    if not normalized_value:
        return None

    try:
        return float(normalized_value)
    except ValueError:
        return None


def _reconcile_shopping_list_amount_after_add(
    grocy_client: GrocyClient,
    *,
    product_id: int,
    requested_amount: float,
    before_items: list[dict] | None = None,
) -> None:
    if requested_amount <= 0:
        return

    supports_amount_reconciliation = all(
        hasattr(grocy_client, attr)
        for attr in ("get_shopping_list", "update_shopping_list_item_amount")
    )
    if not supports_amount_reconciliation:
        return

    try:
        normalized_before_items = (
            before_items
            if isinstance(before_items, list)
            else grocy_client.get_shopping_list()
        )
        after_items = grocy_client.get_shopping_list()
    except Exception:
        return

    normalized_product_id = _safe_int(product_id)

    def _amount_by_item_id(items: list[dict]) -> dict[int, float]:
        amounts: dict[int, float] = {}
        for item in items:
            if _safe_int(item.get("product_id")) != normalized_product_id:
                continue
            item_id = _safe_int(item.get("id"))
            if item_id is None:
                continue
            parsed_item_amount = _parse_float_or_none(item.get("amount"))
            amounts[item_id] = parsed_item_amount if parsed_item_amount else 0.0
        return amounts

    before_amounts = _amount_by_item_id(normalized_before_items)
    after_amounts = _amount_by_item_id(after_items)

    target_item_id: int | None = None
    expected_amount: float | None = None

    new_item_ids = [
        item_id for item_id in after_amounts if item_id not in before_amounts
    ]
    if new_item_ids:
        target_item_id = max(new_item_ids)
        expected_amount = float(requested_amount)
    else:
        shared_item_ids = [
            item_id for item_id in after_amounts if item_id in before_amounts
        ]
        if shared_item_ids:
            target_item_id = max(
                shared_item_ids,
                key=lambda item_id: abs(
                    after_amounts.get(item_id, 0.0) - before_amounts.get(item_id, 0.0)
                ),
            )
            expected_amount = before_amounts.get(target_item_id, 0.0) + float(
                requested_amount
            )

    if target_item_id is None or expected_amount is None:
        return

    current_amount = after_amounts.get(target_item_id)
    if current_amount is not None and abs(current_amount - expected_amount) <= 1e-9:
        return

    normalized_amount = (
        str(int(expected_amount))
        if float(expected_amount).is_integer()
        else str(expected_amount)
    )
    try:
        grocy_client.update_shopping_list_item_amount(
            shopping_list_id=target_item_id,
            amount=normalized_amount,
        )
    except Exception:
        return


def _resolve_best_before_date_for_product(
    grocy_client: GrocyClient,
    product_id: int,
    best_before_date: str = "",
    default_best_before_days: Any = None,
) -> str:
    resolver = getattr(grocy_client, "resolve_best_before_date", None)
    if callable(resolver):
        return resolver(
            product_id=product_id,
            best_before_date=best_before_date,
            default_best_before_days=default_best_before_days,
        )
    return str(best_before_date or "").strip()


def _score_recipe_match(recipe: dict, selected_products: list[str]) -> tuple[int, str]:
    title = str(recipe.get("name") or "")
    normalized_title = title.casefold()
    matches = [
        product
        for product in selected_products
        if product.casefold() in normalized_title
    ]
    reason = (
        f"Passt zu: {', '.join(matches)}"
        if matches
        else "Grundrezept aus Grocy für deine Vorräte"
    )
    return len(matches), reason


def _get_product_image_cache(request: Request):
    return getattr(request.app.state, "product_image_cache", None)


def _get_location_cache(request: Request):
    return getattr(request.app.state, "location_cache", None)


def _get_recipe_suggestion_cache(request: Request):
    return getattr(request.app.state, "recipe_suggestion_cache", None)


def _normalize_recipe_cache_entries(cache: dict | None) -> list[dict]:
    if not isinstance(cache, dict):
        return []

    entries = cache.get("entries")
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]

    if "response" in cache:
        return [cache]

    return []


def _build_recipe_cache_key(
    *,
    location_ids: list[int],
    selected_ids: set[int],
    soon_expiring_only: bool,
    expiring_within_days: int,
) -> dict[str, object]:
    return {
        "location_ids": sorted(int(location_id) for location_id in location_ids),
        "selected_ids": sorted(int(product_id) for product_id in selected_ids),
        "soon_expiring_only": bool(soon_expiring_only),
        "expiring_within_days": max(1, min(int(expiring_within_days), 30)),
    }


def _get_cached_recipe_suggestion_response(
    cache: dict | None,
    *,
    stock_signature: str,
    cache_key: dict[str, object],
) -> dict | None:
    for entry in _normalize_recipe_cache_entries(cache):
        if (
            entry.get("stock_signature") == stock_signature
            and entry.get("response")
            and entry.get("location_ids") == cache_key["location_ids"]
            and entry.get("selected_ids", []) == cache_key["selected_ids"]
            and bool(entry.get("soon_expiring_only")) == cache_key["soon_expiring_only"]
            and int(entry.get("expiring_within_days", 3))
            == cache_key["expiring_within_days"]
        ):
            return entry.get("response")
    return None


def _store_cached_recipe_suggestion_response(
    cache: dict | None,
    *,
    stock_signature: str,
    cache_key: dict[str, object],
    response_payload: dict,
) -> None:
    if cache is None:
        return

    entries = _normalize_recipe_cache_entries(cache)
    normalized_entry = {
        "location_ids": list(cache_key["location_ids"]),
        "selected_ids": list(cache_key["selected_ids"]),
        "soon_expiring_only": bool(cache_key["soon_expiring_only"]),
        "expiring_within_days": int(cache_key["expiring_within_days"]),
        "stock_signature": stock_signature,
        "response": response_payload,
    }

    entries = [
        entry
        for entry in entries
        if not (
            entry.get("location_ids") == normalized_entry["location_ids"]
            and entry.get("selected_ids", []) == normalized_entry["selected_ids"]
            and bool(entry.get("soon_expiring_only"))
            == normalized_entry["soon_expiring_only"]
            and int(
                entry.get(
                    "expiring_within_days",
                    normalized_entry["expiring_within_days"],
                )
            )
            == normalized_entry["expiring_within_days"]
        )
    ]
    entries.append(normalized_entry)
    cache.clear()
    cache["entries"] = entries


def _generate_and_attach_product_picture(
    product_name: str,
    product_id: int,
    detector: IngredientDetector,
    grocy_client: GrocyClient,
    settings: Settings,
) -> None:
    if not settings.image_generation_enabled:
        return

    try:
        image_path = detector.generate_product_image(product_name)
        if not image_path:
            return
        grocy_client.attach_product_picture(product_id, image_path)
    except Exception as error:
        logger.warning(
            "Produktbild konnte nicht automatisch erstellt/gespeichert werden (%s): %s",
            product_name,
            error,
        )


def _get_default_location_id(grocy_client: GrocyClient) -> int:
    try:
        locations = grocy_client.get_locations()
    except Exception:
        locations = []

    for location in locations:
        location_id = _safe_int(location.get("id"))
        if location_id is not None and location_id > 0:
            return location_id

    return 1


def _get_default_quantity_unit_id(grocy_client: GrocyClient) -> int:
    try:
        quantity_units = grocy_client.get_quantity_units()
    except Exception:
        quantity_units = {}

    for unit_id in quantity_units.keys():
        normalized_unit_id = _safe_int(unit_id)
        if normalized_unit_id is not None and normalized_unit_id > 0:
            return normalized_unit_id

    return 1


def _build_scanner_product_description(payload: ScannerProductCreateRequest) -> str:
    description_lines: list[str] = []
    if payload.brand:
        description_lines.append(f"Marke: {payload.brand}")
    if payload.quantity:
        description_lines.append(f"Menge: {payload.quantity}")
    if payload.hint:
        description_lines.append(f"Hinweis: {payload.hint}")
    if payload.nutrition_grade:
        description_lines.append(f"Nutrition-Grade: {payload.nutrition_grade}")
    if payload.ingredients_text:
        description_lines.append(f"Zutaten: {payload.ingredients_text}")

    source_label = str(payload.source or "").strip()
    if source_label:
        description_lines.append(f"Quelle: {source_label}")

    return "\n".join(line for line in description_lines if line).strip()


def _create_and_add_product_to_shopping_list(
    *,
    product_name: str,
    amount: float,
    best_before_date: str,
    product_data: dict[str, Any],
    detector: IngredientDetector,
    grocy_client: GrocyClient,
    settings: Settings,
    barcode: str = "",
) -> DashboardSearchResponse:
    normalized_new_product_name = _normalize_new_product_name(product_name)
    product_data["name"] = normalized_new_product_name or product_name

    product_payload = {
        key: value
        for key, value in product_data.items()
        if key not in {"calories", "carbohydrates", "fat", "protein", "sugar"}
    }
    created_object_id = grocy_client.create_product(product_payload)
    grocy_client.update_product_nutrition(
        product_id=created_object_id,
        calories=product_data.get("calories"),
        carbs=product_data.get("carbohydrates"),
        fat=product_data.get("fat"),
        protein=product_data.get("protein"),
        sugar=product_data.get("sugar"),
    )
    existing_default_best_before_days = (
        grocy_client.get_product_default_best_before_days(created_object_id)
    )
    if not existing_default_best_before_days:
        grocy_client.set_product_default_best_before_days(
            created_object_id,
            product_data.get("default_best_before_days"),
        )

    normalized_barcode = _normalize_barcode_for_lookup(barcode)
    if len(normalized_barcode) >= 8:
        try:
            grocy_client.set_product_barcode(created_object_id, normalized_barcode)
        except Exception as error:
            logger.warning(
                "Barcode %s konnte dem Produkt %s nicht zugewiesen werden: %s",
                normalized_barcode,
                created_object_id,
                error,
            )

    _generate_and_attach_product_picture(
        product_name=product_name,
        product_id=created_object_id,
        detector=detector,
        grocy_client=grocy_client,
        settings=settings,
    )
    resolved_best_before_date = _resolve_best_before_date_for_product(
        grocy_client,
        product_id=created_object_id,
        best_before_date=best_before_date,
        default_best_before_days=product_data.get("default_best_before_days"),
    )
    before_items = (
        grocy_client.get_shopping_list()
        if hasattr(grocy_client, "get_shopping_list")
        else None
    )
    grocy_client.add_product_to_shopping_list(
        created_object_id,
        amount=amount,
        best_before_date=resolved_best_before_date,
    )
    _reconcile_shopping_list_amount_after_add(
        grocy_client,
        product_id=created_object_id,
        requested_amount=float(amount),
        before_items=before_items,
    )

    return DashboardSearchResponse(
        success=True,
        action="created_and_added",
        message=f"{product_name} wurde neu angelegt und zur Einkaufsliste hinzugefügt.",
        product_id=created_object_id,
    )


def _build_stock_signature(
    stock_products: list[dict],
) -> tuple[tuple[str, str, str, str, str], ...]:
    signature_entries: list[tuple[str, str, str, str, str]] = []
    for product in stock_products:
        signature_entries.append(
            (
                str(product.get("id") or ""),
                str(product.get("name") or ""),
                str(product.get("amount") or ""),
                str(product.get("location_id") or ""),
                str(product.get("location_name") or ""),
            )
        )
    return tuple(sorted(signature_entries))


def _safe_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None

    text = str(value).strip()
    if not text:
        return None

    return int(text) if text.isdigit() else None


def _parse_best_before_date(value: object) -> date | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None

    for parser in (
        date.fromisoformat,
        lambda item: date.fromisoformat(item.split("T", 1)[0]),
        lambda item: date.fromisoformat(item.split(" ", 1)[0]),
    ):
        try:
            parsed = parser(raw_value)
            if isinstance(parsed, date):
                return parsed
        except ValueError:
            continue

    return None


def _generate_recipe_suggestions(
    stock_products: list[dict],
    selected_ids: set[int],
    grocy_client: GrocyClient,
    settings: Settings,
) -> RecipeSuggestionResponse:
    if not selected_ids:
        selected_products = [product.get("name", "") for product in stock_products]
    else:
        selected_products = [
            product.get("name", "")
            for product in stock_products
            if product.get("id") in selected_ids
        ]

    if not selected_products:
        return RecipeSuggestionResponse(
            selected_products=[],
            grocy_recipes=[],
            ai_recipes=[],
        )

    grocy_recipes_raw = grocy_client.get_recipes()
    scored = []
    for recipe in grocy_recipes_raw:
        score, reason = _score_recipe_match(recipe, selected_products)
        scored.append((score, recipe, reason))

    scored.sort(key=lambda row: (-row[0], str(row[1].get("name") or "").casefold()))
    grocy_recipes = []
    for _, recipe, reason in scored[:GROCY_RECIPE_SUGGESTION_LIMIT]:
        recipe_id = (
            int(recipe.get("id")) if str(recipe.get("id") or "").isdigit() else None
        )
        missing_products = (
            grocy_client.get_missing_recipe_products(recipe_id)
            if recipe_id is not None
            else []
        )
        recipe_ingredients = (
            grocy_client.get_recipe_ingredients(recipe_id)
            if recipe_id is not None
            else []
        )
        grocy_recipes.append(
            RecipeSuggestionItem(
                recipe_id=recipe_id,
                title=html_to_plain_text(recipe.get("name") or "Unbenanntes Rezept"),
                source="grocy",
                reason=reason,
                preparation=html_to_plain_text(recipe.get("description") or ""),
                ingredients=recipe_ingredients,
                picture_url=_build_dashboard_picture_proxy_url(
                    str(recipe.get("picture_url") or ""),
                    settings,
                ),
                missing_products=missing_products,
            )
        )

    detector = IngredientDetector(settings)
    ai_raw = detector.generate_recipe_suggestions(
        selected_products,
        [item.title for item in grocy_recipes],
    )
    if not isinstance(ai_raw, list):
        ai_raw = []

    if not ai_raw:
        ai_raw = []

    ai_fallback_candidates = [
        {
            "title": f"{', '.join(selected_products[:2])} Pfanne",
            "reason": "Schnelle Resteverwertung aus deinem aktuellen Bestand.",
            "ingredients": [
                f"1 Portion {selected_products[0]}",
                (
                    f"1 Portion {selected_products[1]}"
                    if len(selected_products) > 1
                    else "1 Portion Vorrat nach Wahl"
                ),
            ],
        },
        {
            "title": f"{selected_products[0]} Salat",
            "reason": "Leichtes Rezept, das mit den vorhandenen Zutaten startet.",
            "ingredients": [f"2 Portionen {selected_products[0]}", "1 EL Öl"],
        },
        {
            "title": "Bunte Vorrats-Bowl",
            "reason": "Flexibel mit deinen verfügbaren Zutaten kombinierbar.",
            "ingredients": [
                "1 Handvoll gemischtes Gemüse",
                "1 EL Öl",
                "Gewürze nach Wahl",
            ],
        },
    ]

    ai_recipes: list[RecipeSuggestionItem] = []
    for item in ai_raw[:AI_RECIPE_SUGGESTION_LIMIT]:
        if not isinstance(item, dict):
            continue

        normalized_ingredients = [
            str(ingredient).strip()
            for ingredient in (item.get("ingredients") or [])
            if str(ingredient).strip()
        ]
        if not normalized_ingredients:
            normalized_ingredients = [
                f"1 Portion {product}" for product in selected_products[:4]
            ]

        normalized_ingredients = [
            html_to_plain_text(ingredient)
            for ingredient in normalized_ingredients
            if html_to_plain_text(ingredient)
        ]

        ai_recipes.append(
            RecipeSuggestionItem(
                title=html_to_plain_text(item.get("title") or "KI-Rezept"),
                source="ai",
                reason=html_to_plain_text(item.get("reason") or ""),
                preparation=html_to_plain_text(item.get("preparation") or ""),
                ingredients=normalized_ingredients,
                picture_url="",
            )
        )

    used_ai_titles = {item.title.casefold() for item in ai_recipes if item.title}
    for fallback_item in ai_fallback_candidates:
        if len(ai_recipes) >= AI_RECIPE_SUGGESTION_LIMIT:
            break

        fallback_title = html_to_plain_text(fallback_item.get("title") or "KI-Rezept")
        if not fallback_title or fallback_title.casefold() in used_ai_titles:
            continue

        fallback_ingredients = [
            html_to_plain_text(str(ingredient).strip())
            for ingredient in (fallback_item.get("ingredients") or [])
            if str(ingredient).strip()
        ]

        ai_recipes.append(
            RecipeSuggestionItem(
                title=fallback_title,
                source="ai",
                reason=html_to_plain_text(fallback_item.get("reason") or ""),
                preparation=html_to_plain_text(fallback_item.get("preparation") or ""),
                ingredients=[
                    ingredient for ingredient in fallback_ingredients if ingredient
                ],
                picture_url="",
            )
        )
        used_ai_titles.add(fallback_title.casefold())

    return RecipeSuggestionResponse(
        selected_products=selected_products,
        grocy_recipes=grocy_recipes,
        ai_recipes=ai_recipes,
    )


def prefetch_initial_recipe_suggestions(settings: Settings) -> dict | None:
    if not settings.grocy_api_key:
        return None

    grocy_client = GrocyClient(settings)
    stock_products = grocy_client.get_stock_products()
    response = _generate_recipe_suggestions(
        stock_products=stock_products,
        selected_ids=set(),
        grocy_client=grocy_client,
        settings=settings,
    )
    payload = (
        response.model_dump() if hasattr(response, "model_dump") else response.dict()
    )
    cache_key = _build_recipe_cache_key(
        location_ids=[],
        selected_ids=set(),
        soon_expiring_only=False,
        expiring_within_days=3,
    )
    return {
        "entries": [
            {
                "location_ids": cache_key["location_ids"],
                "selected_ids": cache_key["selected_ids"],
                "soon_expiring_only": cache_key["soon_expiring_only"],
                "expiring_within_days": cache_key["expiring_within_days"],
                "stock_signature": _build_stock_signature(stock_products),
                "response": payload,
            }
        ]
    }


def _variant_from_grocy_product(
    product: dict,
    settings: Settings,
) -> ProductVariantResponse:
    return ProductVariantResponse(
        id=product.get("id"),
        name=product.get("name") or "Unbekanntes Produkt",
        picture_url=_build_dashboard_picture_proxy_url(
            product.get("picture_url") or product.get("picture_file_name") or "",
            settings,
        ),
        source="grocy",
    )


def _build_fallback_variants(
    product_name: str,
    grocy_client: GrocyClient,
    settings: Settings,
    detector: IngredientDetector | None = None,
    include_input_variant: bool = False,
) -> list[ProductVariantResponse]:
    variants: list[ProductVariantResponse] = []
    seen_names: set[str] = set()
    grocy_products = grocy_client.search_products_by_partial_name(product_name)

    for product in grocy_products:
        variant = _variant_from_grocy_product(product, settings)
        normalized_name = variant.name.casefold()
        if normalized_name in seen_names:
            continue
        variants.append(variant)
        seen_names.add(normalized_name)

    if detector is not None:
        ai_suggestions = detector.suggest_similar_products(product_name)
        for item in ai_suggestions:
            suggested_name = str(item.get("name") or "").strip()
            if not suggested_name:
                continue

            suggested_products = grocy_client.search_products_by_partial_name(
                suggested_name
            )

            for product in suggested_products:
                variant = _variant_from_grocy_product(product, settings)
                normalized_name = variant.name.casefold()
                if normalized_name in seen_names:
                    continue
                variants.append(variant)
                seen_names.add(normalized_name)

            normalized_suggestion = suggested_name.casefold()
            if normalized_suggestion not in seen_names:
                variants.append(
                    ProductVariantResponse(
                        id=None,
                        name=suggested_name,
                        picture_url="",
                        source="ai",
                    )
                )
                seen_names.add(normalized_suggestion)

    if include_input_variant:
        variants = _prepend_input_variant_if_no_exact(product_name, variants)

    return variants[:10]


def _prepend_input_variant_if_no_exact(
    product_name: str, variants: list[ProductVariantResponse]
) -> list[ProductVariantResponse]:
    has_exact_match = any(
        variant.name.casefold() == product_name.casefold() for variant in variants
    )
    if has_exact_match:
        return variants

    return [
        ProductVariantResponse(
            id=None,
            name=product_name,
            picture_url="",
            source="input",
        ),
        *variants,
    ]


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_auth),
    settings: Settings = Depends(get_settings),
) -> None:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or credentials.credentials != settings.api_key
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/api/status", response_model=AddonStatusResponse)
def get_status(
    _: None = Depends(require_auth),
    integration_version: str | None = Header(
        default=None, alias="X-HA-Integration-Version"
    ),
    settings: Settings = Depends(get_settings),
):
    restart_required = bool(
        integration_version
        and integration_version != settings.required_integration_version
    )
    reason = (
        f"Installierte Integration {integration_version} weicht von der benötigten Version "
        f"{settings.required_integration_version} ab."
        if restart_required
        else ""
    )

    return {
        "status": "Verbunden",
        "ollama_ready": True,
        "addon_version": settings.addon_version,
        "required_integration_version": settings.required_integration_version,
        "homeassistant_restart_required": restart_required,
        "update_reason": reason,
    }


@router.get("/api/v1/health", response_model=AddonHealthResponse)
def get_health(
    settings: Settings = Depends(get_settings),
):
    return AddonHealthResponse(
        addon_version=settings.addon_version,
        required_integration_version=settings.required_integration_version,
    )


@router.get("/api/v1/capabilities", response_model=AddonCapabilitiesResponse)
def get_capabilities(
    settings: Settings = Depends(get_settings),
):
    return AddonCapabilitiesResponse(
        features={
            "scan_image": True,
            "grocy_sync": bool(settings.grocy_api_key),
            "catalog_rebuild": True,
            "notifications_test": True,
            "recipe_suggestions": True,
            "barcode_lookup": True,
            "shopping_list": bool(settings.grocy_api_key),
            "stock_overview": bool(settings.grocy_api_key),
            "last_scan": True,
        },
        endpoints=[
            "/api/v1/health",
            "/api/v1/capabilities",
            "/api/v1/status",
            "/api/v1/shopping-list",
            "/api/v1/stock",
            "/api/v1/recipes",
            "/api/v1/barcode/{barcode}",
            "/api/v1/scan/image",
            "/api/v1/grocy/sync",
            "/api/v1/catalog/rebuild",
            "/api/v1/last-scan",
            "/api/v1/notifications/test",
        ],
        defaults={
            "scanner_llava_timeout_seconds": settings.scanner_llava_timeout_seconds,
            "dashboard_polling_interval_seconds": settings.dashboard_polling_interval_seconds,
            "notification_global_enabled": settings.notification_global_enabled,
        },
    )


@router.get("/api/v1/status", response_model=AddonStatusResponse)
def get_status_v1(
    payload: dict = Depends(get_status),
):
    return payload


@router.get("/api/v1/shopping-list", response_model=list[ShoppingListItemResponse])
def shopping_list_v1(
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    return dashboard_shopping_list(request, None, settings)


@router.get("/api/v1/stock", response_model=list[StockProductResponse])
def stock_v1(
    request: Request,
    location_ids: str = "",
    include_all_products: bool = False,
    q: str = "",
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    return dashboard_stock_products(
        request,
        location_ids=location_ids,
        include_all_products=include_all_products,
        q=q,
        _=None,
        settings=settings,
    )


@router.get("/api/v1/recipes", response_model=RecipeSuggestionResponse)
def recipes_v1(
    request: Request,
    product_ids: str = "",
    location_ids: str = "",
    soon_expiring_only: bool = False,
    expiring_within_days: int = Query(default=3, ge=1, le=30),
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    payload = RecipeSuggestionRequest(
        product_ids=_parse_csv_int_values(product_ids),
        location_ids=_parse_csv_int_values(location_ids),
        soon_expiring_only=soon_expiring_only,
        expiring_within_days=expiring_within_days,
    )
    return dashboard_recipe_suggestions(payload, request, None, settings)


@router.post("/api/analyze_product", response_model=AnalyzeProductResponse)
def analyze_product(
    payload: AnalyzeProductRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    detector = IngredientDetector(settings)
    try:
        cache = _get_location_cache(request)
        locations = cache.get_locations() if cache else []
        if locations:
            product_data = detector.analyze_product_name(
                payload.name, locations=locations
            )
        else:
            product_data = detector.analyze_product_name(payload.name)
        return AnalyzeProductResponse(product_data=product_data)
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get(
    "/api/dashboard/search-variants", response_model=list[ProductVariantResponse]
)
def dashboard_search_variants(
    q: str,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
    include_ai: bool = False,
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    query, _ = _extract_amount_prefixed_product_input(q)
    if not query:
        return []

    try:
        grocy_client = GrocyClient(settings)
        detector = IngredientDetector(settings) if include_ai else None
        return _build_fallback_variants(
            product_name=query,
            grocy_client=grocy_client,
            settings=settings,
            detector=detector,
            include_input_variant=True,
        )
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post(
    "/api/dashboard/add-existing-product", response_model=DashboardSearchResponse
)
def dashboard_add_existing_product(
    payload: ExistingProductAddRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        normalized_product_name, parsed_amount = _extract_amount_prefixed_product_input(
            payload.product_name
        )
        amount = parsed_amount if parsed_amount is not None else payload.amount

        supports_amount_reconciliation = all(
            hasattr(grocy_client, attr)
            for attr in ("get_shopping_list", "update_shopping_list_item_amount")
        )
        before_items = (
            grocy_client.get_shopping_list() if supports_amount_reconciliation else []
        )
        resolved_best_before_date = _resolve_best_before_date_for_product(
            grocy_client,
            product_id=payload.product_id,
            best_before_date=payload.best_before_date,
        )
        grocy_client.add_product_to_shopping_list(
            payload.product_id,
            amount=amount,
            best_before_date=resolved_best_before_date,
        )
        _reconcile_shopping_list_amount_after_add(
            grocy_client,
            product_id=payload.product_id,
            requested_amount=float(amount),
            before_items=before_items,
        )

        after_items = (
            grocy_client.get_shopping_list() if supports_amount_reconciliation else []
        )

        normalized_product_id = _safe_int(payload.product_id)

        def _amount_by_item_id(items: list[dict]) -> dict[int, float]:
            amounts: dict[int, float] = {}
            for item in items:
                if _safe_int(item.get("product_id")) != normalized_product_id:
                    continue
                item_id = _safe_int(item.get("id"))
                if item_id is None:
                    continue
                parsed_item_amount = _parse_float_or_none(item.get("amount"))
                amounts[item_id] = parsed_item_amount if parsed_item_amount else 0.0
            return amounts

        before_amounts = _amount_by_item_id(before_items)
        after_amounts = _amount_by_item_id(after_items)

        target_item_id: int | None = None
        expected_amount: float | None = None

        new_item_ids = [
            item_id for item_id in after_amounts if item_id not in before_amounts
        ]
        if new_item_ids:
            target_item_id = max(new_item_ids)
            expected_amount = float(amount)
        else:
            shared_item_ids = [
                item_id for item_id in after_amounts if item_id in before_amounts
            ]
            if shared_item_ids:
                target_item_id = max(
                    shared_item_ids,
                    key=lambda item_id: abs(
                        after_amounts.get(item_id, 0.0)
                        - before_amounts.get(item_id, 0.0)
                    ),
                )
                expected_amount = before_amounts.get(target_item_id, 0.0) + float(
                    amount
                )

        if (
            supports_amount_reconciliation
            and target_item_id is not None
            and expected_amount is not None
        ):
            current_amount = after_amounts.get(target_item_id)
            if current_amount is None or abs(current_amount - expected_amount) > 1e-9:
                normalized_amount = (
                    str(int(expected_amount))
                    if float(expected_amount).is_integer()
                    else str(expected_amount)
                )
                grocy_client.update_shopping_list_item_amount(
                    shopping_list_id=target_item_id,
                    amount=normalized_amount,
                )

        return DashboardSearchResponse(
            success=True,
            action="existing_added",
            message=(
                f"{normalized_product_name or payload.product_name} "
                "wurde zur Einkaufsliste hinzugefügt."
            ),
            product_id=payload.product_id,
        )
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/dashboard/search", response_model=DashboardSearchResponse)
def dashboard_search(
    payload: AnalyzeProductRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    product_name, parsed_amount = _extract_amount_prefixed_product_input(payload.name)
    if not product_name:
        raise HTTPException(status_code=400, detail="Bitte Produktname eingeben")

    amount = parsed_amount if parsed_amount is not None else payload.amount

    detector = IngredientDetector(settings)
    grocy_client = GrocyClient(settings)

    try:
        if not payload.force_create:
            existing_product = grocy_client.find_product_by_name(product_name)
            if existing_product:
                existing_product_id = int(existing_product.get("id"))
                resolved_best_before_date = _resolve_best_before_date_for_product(
                    grocy_client,
                    product_id=existing_product_id,
                    best_before_date=payload.best_before_date,
                )
                before_items = (
                    grocy_client.get_shopping_list()
                    if hasattr(grocy_client, "get_shopping_list")
                    else None
                )
                grocy_client.add_product_to_shopping_list(
                    existing_product_id,
                    amount=amount,
                    best_before_date=resolved_best_before_date,
                )
                _reconcile_shopping_list_amount_after_add(
                    grocy_client,
                    product_id=existing_product_id,
                    requested_amount=float(amount),
                    before_items=before_items,
                )
                return DashboardSearchResponse(
                    success=True,
                    action="existing_added",
                    message=f"{product_name} war vorhanden und wurde zur Einkaufsliste hinzugefügt.",
                )

        fallback_variants = _build_fallback_variants(
            product_name=product_name,
            grocy_client=grocy_client,
            settings=settings,
        )
        if fallback_variants and not payload.force_create:
            fallback_variants = _prepend_input_variant_if_no_exact(
                product_name, fallback_variants
            )
            return DashboardSearchResponse(
                success=False,
                action="variant_selection_required",
                message=(
                    f"{product_name} wurde nicht direkt als Produkt übernommen. "
                    "Bitte wähle ein passendes Produkt aus den Vorschlägen."
                ),
                variants=fallback_variants,
            )

        cache = _get_location_cache(request)
        locations = cache.get_locations() if cache else []
        if locations:
            product_data = detector.analyze_product_name(
                product_name, locations=locations
            )
        else:
            product_data = detector.analyze_product_name(product_name)
        return _create_and_add_product_to_shopping_list(
            product_name=product_name,
            amount=amount,
            best_before_date=payload.best_before_date,
            product_data=product_data,
            detector=detector,
            grocy_client=grocy_client,
            settings=settings,
        )
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/v1/grocy/sync", response_model=DashboardSearchResponse)
def sync_product_to_grocy(
    payload: AnalyzeProductRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    return dashboard_search(payload, request, None, settings)


@router.get("/api/dashboard/barcode/{barcode}", response_model=BarcodeProductResponse)
def dashboard_barcode_lookup(
    barcode: str,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    normalized_barcode = _normalize_barcode_for_lookup(barcode)
    if len(normalized_barcode) < 8:
        raise HTTPException(status_code=400, detail="Ungültiger Barcode")

    grocy_client = GrocyClient(settings)
    barcode_candidates = _build_barcode_lookup_candidates(normalized_barcode)

    try:
        off_barcode, product = _try_openfoodfacts_lookup(barcode_candidates)
        if off_barcode:
            return BarcodeProductResponse(
                barcode=off_barcode,
                found=True,
                product_name=str(product.get("product_name") or ""),
                brand=str(product.get("brands") or ""),
                quantity=str(product.get("quantity") or ""),
                ingredients_text=str(
                    product.get("ingredients_text_de")
                    or product.get("ingredients_text")
                    or ""
                ),
                nutrition_grade=str(product.get("nutrition_grades") or "").upper(),
            )

        for barcode_candidate in barcode_candidates:
            grocy_product = grocy_client.find_product_by_barcode(barcode_candidate)
            if grocy_product:
                return BarcodeProductResponse(
                    barcode=barcode_candidate,
                    found=True,
                    product_name=str(grocy_product.get("name") or ""),
                    source="Grocy",
                )

        return BarcodeProductResponse(
            barcode=normalized_barcode,
            found=False,
        )
    except requests.RequestException as error:
        logger.warning(
            "OpenFoodFacts lookup failed for barcode %s: %s",
            normalized_barcode,
            error,
        )
        for barcode_candidate in barcode_candidates:
            grocy_product = grocy_client.find_product_by_barcode(barcode_candidate)
            if grocy_product:
                return BarcodeProductResponse(
                    barcode=barcode_candidate,
                    found=True,
                    product_name=str(grocy_product.get("name") or ""),
                    source="Grocy",
                )
        return BarcodeProductResponse(
            barcode=normalized_barcode,
            found=False,
            source="OpenFoodFacts",
        )
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(
            status_code=500, detail="Barcode konnte nicht abgefragt werden"
        ) from error


@router.get("/api/v1/barcode/{barcode}", response_model=BarcodeProductResponse)
def barcode_lookup_v1(
    barcode: str,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    return dashboard_barcode_lookup(barcode, request, None, settings)


@router.post("/api/dashboard/scanner/llava", response_model=ScannerLlavaResponse)
def dashboard_scanner_llava(
    payload: ScannerLlavaRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    image_base64 = str(payload.image_base64 or "").strip()
    if not image_base64:
        raise HTTPException(status_code=400, detail="Bilddaten fehlen")

    llava_timeout_seconds = max(
        10, min(120, int(settings.scanner_llava_timeout_seconds))
    )
    if not _acquire_llava_request_slot(llava_timeout_seconds):
        raise HTTPException(
            status_code=429,
            detail="LLaVA-Erkennung läuft bereits. Bitte kurz warten.",
        )

    detector = IngredientDetector(settings)
    try:
        detection = detector.detect_product_from_image(
            image_base64, timeout_seconds=llava_timeout_seconds
        )
        if not any(detection.values()):
            response = ScannerLlavaResponse(success=False)
            _store_last_scan_result(response)
            return response

        response = ScannerLlavaResponse(
            success=True,
            product_name=detection.get("product_name", ""),
            brand=detection.get("brand", ""),
            hint=detection.get("hint", ""),
        )
        _store_last_scan_result(response)
        return response
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(
            status_code=500, detail="LLaVA-Erkennung konnte nicht durchgeführt werden"
        ) from error
    finally:
        _release_llava_request_slot()


@router.post("/api/v1/scan/image", response_model=ScannerLlavaResponse)
def scan_image_v1(
    payload: ScannerLlavaRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    return dashboard_scanner_llava(payload, request, None, settings)


@router.get("/api/v1/last-scan", response_model=AddonLastScanResponse)
def last_scan_v1(
    _: None = Depends(require_auth),
):
    result = LAST_SCAN_RESULT.get("result")
    return AddonLastScanResponse(
        available=bool(result),
        updated_at=str(LAST_SCAN_RESULT.get("updated_at") or ""),
        result=result if isinstance(result, dict) else None,
    )


@router.post("/api/v1/catalog/rebuild", response_model=AddonCatalogRebuildResponse)
def rebuild_catalog_v1(
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    location_cache = _get_location_cache(request)
    image_cache = _get_product_image_cache(request)

    refreshed_locations = (
        int(location_cache.refresh_locations()) if location_cache else 0
    )
    refreshed_product_images = (
        int(image_cache.refresh_all_product_images()) if image_cache else 0
    )

    prefetched_recipe_suggestions = 0
    prefetched_payload = prefetch_initial_recipe_suggestions(settings)
    if isinstance(prefetched_payload, dict):
        cache = _get_recipe_suggestion_cache(request)
        if cache is not None:
            cache.clear()
            cache.update(prefetched_payload)
        response_payload = prefetched_payload.get("response")
        if isinstance(response_payload, dict):
            prefetched_recipe_suggestions = len(
                response_payload.get("grocy_recipes", [])
            ) + len(response_payload.get("ai_recipes", []))

    return AddonCatalogRebuildResponse(
        refreshed_locations=refreshed_locations,
        refreshed_product_images=refreshed_product_images,
        prefetched_recipe_suggestions=prefetched_recipe_suggestions,
    )


@router.post(
    "/api/dashboard/scanner/create-product", response_model=DashboardSearchResponse
)
def dashboard_scanner_create_product(
    payload: ScannerProductCreateRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    product_name = _normalize_new_product_name(payload.product_name)
    if not product_name:
        raise HTTPException(status_code=400, detail="Bitte Produktname eingeben")

    detector = IngredientDetector(settings)
    grocy_client = GrocyClient(settings)

    try:
        product_data = {
            "name": product_name,
            "description": _build_scanner_product_description(payload),
            "location_id": _get_default_location_id(grocy_client),
            "qu_id_purchase": _get_default_quantity_unit_id(grocy_client),
            "qu_id_stock": _get_default_quantity_unit_id(grocy_client),
            "calories": 0,
            "carbohydrates": 0,
            "fat": 0,
            "protein": 0,
            "sugar": 0,
            "default_best_before_days": 0,
        }
        return _create_and_add_product_to_shopping_list(
            product_name=product_name,
            amount=payload.amount,
            best_before_date=payload.best_before_date,
            product_data=product_data,
            detector=detector,
            grocy_client=grocy_client,
            settings=settings,
            barcode=payload.barcode,
        )
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(
            status_code=500,
            detail="Produkt konnte nicht aus dem Scanner angelegt werden",
        ) from error


@router.get("/api/dashboard/product-picture")
def dashboard_product_picture(
    src: str,
    request: Request,
    size: str = "thumb",
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    if not src:
        raise HTTPException(status_code=400, detail="Bildquelle fehlt")

    src = _normalize_dashboard_picture_source_url(src)

    parsed_src = urlparse(src)
    parsed_grocy = urlparse(settings.grocy_base_url)
    if (
        parsed_src.scheme not in ("http", "https")
        or parsed_src.netloc != parsed_grocy.netloc
    ):
        raise HTTPException(status_code=400, detail="Ungültige Bildquelle")

    sized_src = _apply_picture_size(src, size)

    image_cache = _get_product_image_cache(request)
    if image_cache:
        cached_content, cached_media_type = image_cache.get_cached_image(sized_src)
        if cached_content is not None:
            return Response(
                content=cached_content,
                media_type=cached_media_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )

    parsed_src = urlparse(sized_src)
    candidate_urls = [sized_src]
    if parsed_src.path.startswith("/api/files/"):
        candidate_urls.append(
            ParseResult(
                scheme=parsed_src.scheme,
                netloc=parsed_src.netloc,
                path=parsed_src.path.removeprefix("/api"),
                params=parsed_src.params,
                query=parsed_src.query,
                fragment=parsed_src.fragment,
            ).geturl()
        )
    elif parsed_src.path.startswith("/files/"):
        candidate_urls.append(
            ParseResult(
                scheme=parsed_src.scheme,
                netloc=parsed_src.netloc,
                path=f"/api{parsed_src.path}",
                params=parsed_src.params,
                query=parsed_src.query,
                fragment=parsed_src.fragment,
            ).geturl()
        )

    response = None
    for index, candidate_url in enumerate(candidate_urls):
        logger.info("Lade Produktbild via Proxy: %s", candidate_url)
        try:
            response = requests.get(
                candidate_url,
                headers={"GROCY-API-KEY": settings.grocy_api_key},
                timeout=30,
            )
            response.raise_for_status()
            break
        except requests.HTTPError as error:
            is_not_found = (
                error.response is not None and error.response.status_code == 404
            )
            has_fallback = index < len(candidate_urls) - 1
            if is_not_found and has_fallback:
                logger.info(
                    "Bild unter %s nicht gefunden, versuche Fallback-URL %s",
                    candidate_url,
                    candidate_urls[index + 1],
                )
                continue
            log_api_error(
                logger,
                request=request,
                status_code=404,
                message="Bild nicht gefunden",
                details=[{"source": candidate_url}],
                exc=error,
            )
            raise HTTPException(
                status_code=404, detail="Bild nicht gefunden"
            ) from error
        except requests.RequestException as error:
            log_api_error(
                logger,
                request=request,
                status_code=502,
                message="Produktbild konnte nicht geladen werden",
                details=[{"source": candidate_url}],
                exc=error,
            )
            raise HTTPException(
                status_code=502,
                detail="Produktbild konnte nicht geladen werden",
            ) from error

    if response is None:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden")

    content_type = response.headers.get("Content-Type", "image/jpeg")
    return Response(
        content=response.content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/api/dashboard/product-picture-cache/refresh")
def refresh_product_picture_cache(
    request: Request,
    _: None = Depends(require_auth),
):
    image_cache = _get_product_image_cache(request)
    if not image_cache:
        raise HTTPException(status_code=503, detail="Bildcache nicht verfügbar")

    refreshed = image_cache.refresh_all_product_images()
    return {"success": True, "refreshed_images": refreshed}


@router.get(
    "/api/dashboard/shopping-list", response_model=list[ShoppingListItemResponse]
)
def dashboard_shopping_list(
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        items = grocy_client.get_shopping_list()
        return [
            ShoppingListItemResponse(
                id=item.get("id"),
                amount=str(item.get("amount") or "1"),
                product_id=item.get("product_id"),
                product_name=item.get("product_name") or "Unbekanntes Produkt",
                note=item.get("note") or "",
                picture_url=_build_dashboard_picture_proxy_url(
                    _extract_shopping_item_picture_value(item),
                    settings,
                ),
                location_name=str(item.get("location_name") or ""),
                in_stock=str(item.get("in_stock") or ""),
                best_before_date=str(item.get("best_before_date") or ""),
                default_amount=str(item.get("default_amount") or ""),
                calories=str(item.get("calories") or ""),
                carbs=str(item.get("carbs") or ""),
                fat=str(item.get("fat") or ""),
                protein=str(item.get("protein") or ""),
                sugar=str(item.get("sugar") or ""),
            )
            for item in items
        ]
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/api/dashboard/locations", response_model=list[LocationResponse])
def dashboard_locations(
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        cache = _get_location_cache(request)
        locations = cache.get_locations() if cache else None
        if locations is None:
            grocy_client = GrocyClient(settings)
            locations = grocy_client.get_locations()

        return [LocationResponse(**item) for item in locations]
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/api/dashboard/stock-products", response_model=list[StockProductResponse])
def dashboard_stock_products(
    request: Request,
    location_ids: str = "",
    include_all_products: bool = False,
    q: str = "",
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        selected_location_ids = [
            int(value.strip())
            for value in location_ids.split(",")
            if value.strip().isdigit()
        ]
        grocy_client = GrocyClient(settings)
        stock_products = grocy_client.get_storage_products(
            selected_location_ids if selected_location_ids else None,
            include_all_products=include_all_products,
            search_query=q,
        )
        return [
            StockProductResponse(
                **{
                    **item,
                    "picture_url": _build_dashboard_picture_proxy_url(
                        str(item.get("picture_url") or ""),
                        settings,
                    ),
                }
            )
            for item in stock_products
        ]
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/api/dashboard/products/{product_id}/nutrition")
def dashboard_product_nutrition(
    product_id: int,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        return grocy_client.get_product_nutrition(product_id)
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.delete("/api/dashboard/products/{product_id}/picture")
def dashboard_delete_product_picture(
    product_id: int,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        grocy_client.clear_product_picture(product_id)
        return {"success": True, "message": "Produktbild wurde gelöscht."}
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/dashboard/stock-products/{stock_id}/consume")
def dashboard_consume_stock_product(
    stock_id: int,
    payload: StockProductConsumeRequest,
    request: Request,
    product_id: int | None = Query(default=None),
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        stock_entries = grocy_client.get_stock_entries()
        matched_entry = None
        matched_stock_id: int | None = None
        normalized_product_id = int(product_id or 0)

        if normalized_product_id > 0:
            for entry in stock_entries:
                if int(entry.get("product_id") or 0) != normalized_product_id:
                    continue
                candidate_stock_id = int(entry.get("stock_id") or entry.get("id") or 0)
                if candidate_stock_id == stock_id:
                    matched_entry = entry
                    matched_stock_id = (
                        candidate_stock_id if candidate_stock_id > 0 else None
                    )
                    break
                if matched_entry is None:
                    matched_entry = entry
                    matched_stock_id = (
                        candidate_stock_id if candidate_stock_id > 0 else None
                    )

        if matched_entry is None:
            matched_entry = next(
                (
                    entry
                    for entry in stock_entries
                    if int(entry.get("stock_id") or entry.get("id") or 0) == stock_id
                ),
                None,
            )
            if matched_entry:
                candidate_stock_id = int(
                    matched_entry.get("stock_id") or matched_entry.get("id") or 0
                )
                matched_stock_id = (
                    candidate_stock_id if candidate_stock_id > 0 else None
                )

        if matched_entry is None:
            # Fallback für Clients, die mangels stock_id auf product_id umschalten.
            matched_entry = next(
                (
                    entry
                    for entry in stock_entries
                    if int(entry.get("product_id") or 0) == stock_id
                ),
                None,
            )
            if matched_entry:
                candidate_stock_id = int(
                    matched_entry.get("stock_id") or matched_entry.get("id") or 0
                )
                matched_stock_id = (
                    candidate_stock_id if candidate_stock_id > 0 else None
                )

        if not matched_entry:
            raise HTTPException(
                status_code=404, detail="Bestandseintrag nicht gefunden"
            )

        product_id = int(matched_entry.get("product_id") or 0)
        if product_id <= 0:
            raise HTTPException(status_code=400, detail="Ungültiger Produkteintrag")

        grocy_client.consume_stock_product(
            product_id=product_id,
            amount=payload.amount,
            stock_id=matched_stock_id,
        )
        return {"success": True, "message": "Produkt wurde verbraucht."}
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.delete("/api/dashboard/stock-products/{stock_id}")
def dashboard_delete_stock_product(
    stock_id: int,
    request: Request,
    product_id: int | None = Query(default=None),
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        stock_entries = grocy_client.get_stock_entries()
        matched_entry = None
        normalized_product_id = int(product_id or 0)

        if normalized_product_id > 0:
            for entry in stock_entries:
                if int(entry.get("product_id") or 0) != normalized_product_id:
                    continue
                candidate_stock_id = int(entry.get("stock_id") or entry.get("id") or 0)
                if candidate_stock_id == stock_id:
                    matched_entry = entry
                    break
                if matched_entry is None:
                    matched_entry = entry

        if not matched_entry:
            matched_entry = next(
                (
                    entry
                    for entry in stock_entries
                    if int(entry.get("stock_id") or entry.get("id") or 0) == stock_id
                ),
                None,
            )
        if not matched_entry:
            matched_entry = next(
                (
                    entry
                    for entry in stock_entries
                    if int(entry.get("product_id") or 0) == stock_id
                ),
                None,
            )
        if not matched_entry:
            raise HTTPException(
                status_code=404, detail="Bestandseintrag nicht gefunden"
            )

        resolved_product_id = int(matched_entry.get("product_id") or 0)
        if resolved_product_id <= 0:
            resolved_product_id = int(matched_entry.get("id") or 0)
        if resolved_product_id <= 0:
            resolved_product_id = stock_id

        if resolved_product_id <= 0:
            raise HTTPException(status_code=400, detail="Ungültiger Produkteintrag")

        grocy_client.delete_product(resolved_product_id)
        return {"success": True, "message": "Produkt wurde gelöscht."}
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.put("/api/dashboard/stock-products/{stock_id}")
def dashboard_update_stock_product(
    stock_id: int,
    payload: StockProductUpdateRequest,
    request: Request,
    product_id: int | None = Query(default=None),
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        stock_entries = grocy_client.get_stock_entries()
        matched_entry = None
        normalized_product_id = int(product_id or 0)

        if normalized_product_id > 0:
            for entry in stock_entries:
                if int(entry.get("product_id") or 0) != normalized_product_id:
                    continue
                candidate_stock_id = int(entry.get("stock_id") or entry.get("id") or 0)
                if candidate_stock_id == stock_id:
                    matched_entry = entry
                    break
                if matched_entry is None:
                    matched_entry = entry

        if not matched_entry:
            matched_entry = next(
                (
                    entry
                    for entry in stock_entries
                    if int(entry.get("stock_id") or entry.get("id") or 0) == stock_id
                ),
                None,
            )
        if not matched_entry:
            matched_entry = next(
                (
                    entry
                    for entry in stock_entries
                    if int(entry.get("product_id") or 0) == stock_id
                ),
                None,
            )
        if matched_entry:
            resolved_product_id = int(matched_entry.get("product_id") or 0)
            if resolved_product_id <= 0:
                raise HTTPException(status_code=400, detail="Ungültiger Produkteintrag")

            resolved_stock_id = int(matched_entry.get("stock_id") or 0)
            if resolved_stock_id <= 0:
                resolved_stock_id = int(matched_entry.get("id") or 0)
            if resolved_stock_id <= 0:
                resolved_stock_id = (
                    grocy_client.resolve_stock_entry_id_for_product(
                        product_id=resolved_product_id,
                        location_id=int(matched_entry.get("location_id") or 0) or None,
                    )
                    or 0
                )
            current_amount = _parse_float_or_none(matched_entry.get("amount"))
            current_best_before_date = str(
                matched_entry.get("best_before_date")
                or matched_entry.get("best_before_date_calculated")
                or ""
            ).strip()
            current_location_id = int(matched_entry.get("location_id") or 0) or None
            has_current_best_before_date = any(
                matched_entry.get(key) is not None
                for key in ("best_before_date", "best_before_date_calculated")
            )
        else:
            if normalized_product_id <= 0:
                raise HTTPException(
                    status_code=404, detail="Bestandseintrag nicht gefunden"
                )
            resolved_product_id = normalized_product_id
            resolved_stock_id = (
                grocy_client.resolve_stock_entry_id_for_product(
                    product_id=resolved_product_id,
                )
                or 0
            )
            current_amount = None
            current_best_before_date = ""
            current_location_id = None
            has_current_best_before_date = False

        requested_location_id = (
            int(payload.location_id) if payload.location_id is not None else None
        )
        should_update_location = (
            requested_location_id is not None
            and requested_location_id > 0
            and requested_location_id != current_location_id
        )
        should_update_best_before_date = has_current_best_before_date and (
            str(payload.best_before_date or "").strip() != current_best_before_date
        )

        should_update_inventory = (
            current_amount is None or abs(current_amount - payload.amount) > 1e-9
        )

        if should_update_location and requested_location_id is not None:
            grocy_client.update_product_location(
                product_id=resolved_product_id,
                location_id=requested_location_id,
            )

        if should_update_inventory:
            if resolved_stock_id > 0:
                grocy_client.set_product_inventory(
                    product_id=resolved_product_id,
                    amount=payload.amount,
                    stock_id=resolved_stock_id,
                )
            else:
                if payload.amount > 0:
                    grocy_client.add_product_to_stock(
                        product_id=resolved_product_id,
                        amount=payload.amount,
                        best_before_date=payload.best_before_date,
                    )
                else:
                    grocy_client.set_product_inventory(
                        product_id=resolved_product_id,
                        amount=0,
                    )
        if (
            resolved_stock_id > 0
            and payload.amount > 0
            and (should_update_best_before_date or should_update_location)
        ):
            grocy_client.update_stock_entry(
                stock_id=resolved_stock_id,
                amount=payload.amount,
                best_before_date=payload.best_before_date,
                location_id=requested_location_id,
            )
        grocy_client.update_product_nutrition(
            product_id=resolved_product_id,
            calories=payload.calories,
            carbs=payload.carbs,
            fat=payload.fat,
            protein=payload.protein,
            sugar=payload.sugar,
        )
        return {"success": True, "message": "Bestandseintrag wurde aktualisiert."}
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post(
    "/api/dashboard/recipe-suggestions", response_model=RecipeSuggestionResponse
)
def dashboard_recipe_suggestions(
    payload: RecipeSuggestionRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    selected_ids = set(payload.product_ids)

    try:
        grocy_client = GrocyClient(settings)

        stock_products = (
            grocy_client.get_stock_products(payload.location_ids)
            if payload.location_ids
            else grocy_client.get_stock_products()
        )

        if payload.soon_expiring_only:
            days = max(1, min(int(payload.expiring_within_days), 30))
            today = date.today()
            deadline = today + timedelta(days=days)

            expiring_product_ids: set[int] = set()
            for entry in grocy_client.get_stock_entries(payload.location_ids):
                product_id = _safe_int(entry.get("product_id"))
                if product_id is None:
                    continue

                best_before = _parse_best_before_date(
                    entry.get("best_before_date")
                    or entry.get("best_before_date_calculated")
                )
                if best_before is None:
                    continue

                if today <= best_before <= deadline:
                    expiring_product_ids.add(product_id)

            stock_products = [
                product
                for product in stock_products
                if product.get("id") in expiring_product_ids
            ]
            selected_ids = {
                product_id
                for product_id in selected_ids
                if product_id in expiring_product_ids
            }

        cache = _get_recipe_suggestion_cache(request)
        stock_signature = _build_stock_signature(stock_products)
        cache_key = _build_recipe_cache_key(
            location_ids=payload.location_ids,
            selected_ids=selected_ids,
            soon_expiring_only=payload.soon_expiring_only,
            expiring_within_days=payload.expiring_within_days,
        )
        cached_payload = _get_cached_recipe_suggestion_response(
            cache,
            stock_signature=stock_signature,
            cache_key=cache_key,
        )
        if cached_payload:
            logger.info(
                "Nutze Rezeptvorschlags-Cache (Bestand unverändert, soon_expiring_only=%s)",
                payload.soon_expiring_only,
            )
            return RecipeSuggestionResponse(**cached_payload)

        response = _generate_recipe_suggestions(
            stock_products=stock_products,
            selected_ids=selected_ids,
            grocy_client=grocy_client,
            settings=settings,
        )

        if cache is not None:
            _store_cached_recipe_suggestion_response(
                cache,
                stock_signature=stock_signature,
                cache_key=cache_key,
                response_payload=(
                    response.model_dump()
                    if hasattr(response, "model_dump")
                    else response.dict()
                ),
            )

        return response
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/dashboard/recipe/{recipe_id}/add-missing")
def dashboard_add_missing_recipe_products(
    recipe_id: int,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        missing_products = grocy_client.get_missing_recipe_products(recipe_id)
        added_count = 0
        for product in missing_products:
            product_id = product.get("id")
            if isinstance(product_id, int):
                grocy_client.add_product_to_shopping_list(product_id)
                added_count += 1

        return {
            "success": True,
            "added_items": added_count,
            "message": f"{added_count} fehlende Produkte wurden zur Einkaufsliste hinzugefügt.",
        }
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.put("/api/dashboard/shopping-list/item/{shopping_list_id}/note")
def dashboard_update_shopping_list_item_note(
    shopping_list_id: int,
    payload: ShoppingListNoteUpdateRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        shopping_items = grocy_client.get_shopping_list()
        selected_item = next(
            (item for item in shopping_items if item.get("id") == shopping_list_id),
            None,
        )
        if selected_item is None:
            raise HTTPException(
                status_code=404, detail="Einkaufslisten-Eintrag nicht gefunden"
            )

        grocy_client.update_shopping_list_item_note(
            shopping_list_id=shopping_list_id,
            note=payload.note,
            current_best_before_date=str(selected_item.get("best_before_date") or ""),
        )
        return {
            "success": True,
            "message": f"Notiz für Eintrag {shopping_list_id} aktualisiert.",
        }
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.put("/api/dashboard/shopping-list/item/{shopping_list_id}/best-before")
def dashboard_update_shopping_list_item_best_before_date(
    shopping_list_id: int,
    payload: ShoppingListBestBeforeDateUpdateRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        shopping_items = grocy_client.get_shopping_list()
        selected_item = next(
            (item for item in shopping_items if item.get("id") == shopping_list_id),
            None,
        )
        if selected_item is None:
            raise HTTPException(
                status_code=404, detail="Einkaufslisten-Eintrag nicht gefunden"
            )

        grocy_client.update_shopping_list_item_best_before_date(
            shopping_list_id=shopping_list_id,
            best_before_date=payload.best_before_date,
            current_note=str(selected_item.get("note") or ""),
        )
        return {
            "success": True,
            "message": f"MHD für Eintrag {shopping_list_id} aktualisiert.",
        }
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/dashboard/shopping-list/item/{shopping_list_id}/best-before/reset")
def dashboard_reset_shopping_list_item_best_before_date(
    shopping_list_id: int,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        shopping_items = grocy_client.get_shopping_list()
        selected_item = next(
            (item for item in shopping_items if item.get("id") == shopping_list_id),
            None,
        )
        if selected_item is None:
            raise HTTPException(
                status_code=404, detail="Einkaufslisten-Eintrag nicht gefunden"
            )

        grocy_client.update_shopping_list_item_best_before_date(
            shopping_list_id=shopping_list_id,
            best_before_date="",
            current_note=str(selected_item.get("note") or ""),
        )
        return {
            "success": True,
            "message": f"MHD für Eintrag {shopping_list_id} zurückgesetzt.",
            "best_before_date": "",
        }
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.delete("/api/dashboard/shopping-list/item/{shopping_list_id}")
def dashboard_delete_shopping_list_item(
    shopping_list_id: int,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        shopping_items = grocy_client.get_shopping_list()
        selected_item = next(
            (item for item in shopping_items if item.get("id") == shopping_list_id),
            None,
        )
        if selected_item is None:
            raise HTTPException(
                status_code=404, detail="Einkaufslisten-Eintrag nicht gefunden"
            )

        grocy_client.delete_shopping_list_item(
            shopping_list_id,
            amount=str(selected_item.get("amount") or "1"),
        )
        return {
            "success": True,
            "message": f"Eintrag {shopping_list_id} gelöscht.",
        }
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.put("/api/dashboard/shopping-list/item/{shopping_list_id}/amount")
def dashboard_update_shopping_list_item_amount(
    shopping_list_id: int,
    payload: ShoppingListAmountUpdateRequest,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        shopping_items = grocy_client.get_shopping_list()
        selected_item = next(
            (item for item in shopping_items if item.get("id") == shopping_list_id),
            None,
        )
        if selected_item is None:
            raise HTTPException(
                status_code=404, detail="Einkaufslisten-Eintrag nicht gefunden"
            )

        amount = payload.amount
        normalized_amount = (
            str(int(amount)) if float(amount).is_integer() else str(amount)
        )

        grocy_client.update_shopping_list_item_amount(
            shopping_list_id=shopping_list_id,
            amount=normalized_amount,
        )
        return {
            "success": True,
            "amount": normalized_amount,
            "message": f"Menge für Eintrag {shopping_list_id} aktualisiert.",
        }
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/dashboard/shopping-list/item/{shopping_list_id}/amount/increment")
def dashboard_increment_shopping_list_item_amount(
    shopping_list_id: int,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        shopping_items = grocy_client.get_shopping_list()
        selected_item = next(
            (item for item in shopping_items if item.get("id") == shopping_list_id),
            None,
        )
        if selected_item is None:
            raise HTTPException(
                status_code=404, detail="Einkaufslisten-Eintrag nicht gefunden"
            )

        current_amount_raw = str(selected_item.get("amount") or "1").replace(",", ".")
        try:
            current_amount = float(current_amount_raw)
        except ValueError:
            current_amount = 1.0

        updated_amount = current_amount + 1
        if float(updated_amount).is_integer():
            normalized_amount = str(int(updated_amount))
        else:
            normalized_amount = str(updated_amount)

        grocy_client.update_shopping_list_item_amount(
            shopping_list_id=shopping_list_id,
            amount=normalized_amount,
        )
        return {
            "success": True,
            "amount": normalized_amount,
            "message": f"Menge für Eintrag {shopping_list_id} erhöht.",
        }
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/dashboard/shopping-list/item/{shopping_list_id}/complete")
def dashboard_complete_shopping_list_item(
    shopping_list_id: int,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        shopping_items = grocy_client.get_shopping_list()
        selected_item = next(
            (item for item in shopping_items if item.get("id") == shopping_list_id),
            None,
        )
        if selected_item is None:
            raise HTTPException(
                status_code=404, detail="Einkaufslisten-Eintrag nicht gefunden"
            )

        product_id = selected_item.get("product_id")
        if product_id is None:
            raise HTTPException(status_code=400, detail="Produkt-ID für Eintrag fehlt")

        resolved_best_before_date = _resolve_best_before_date_for_product(
            grocy_client,
            product_id=int(product_id),
            best_before_date=str(selected_item.get("best_before_date") or ""),
            default_best_before_days=selected_item.get("default_amount"),
        )
        grocy_client.complete_shopping_list_item(
            shopping_list_id,
            product_id=int(product_id),
            amount=str(selected_item.get("amount") or "1"),
            best_before_date=resolved_best_before_date,
        )
        return {
            "success": True,
            "message": f"Eintrag {shopping_list_id} als eingekauft markiert.",
        }
    except HTTPException:
        raise
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/dashboard/shopping-list/{shopping_list_id}/complete")
def dashboard_complete_shopping_list_item_legacy(
    shopping_list_id: int,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    return dashboard_complete_shopping_list_item(
        shopping_list_id=shopping_list_id,
        request=request,
        _=_,
        settings=settings,
    )


@router.post("/api/dashboard/shopping-list/complete")
def dashboard_complete_shopping_list(
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        completed_items = grocy_client.complete_shopping_list()
        return {
            "success": True,
            "completed_items": completed_items,
            "message": f"Einkauf abgeschlossen ({completed_items} Einträge als eingekauft markiert).",
        }
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.delete("/api/dashboard/shopping-list/clear")
def dashboard_clear_shopping_list(
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        removed_items = grocy_client.clear_shopping_list()
        return {
            "success": True,
            "removed_items": removed_items,
            "message": f"Einkaufsliste geleert ({removed_items} Einträge entfernt).",
        }
    except Exception as error:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message=str(error),
            exc=error,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


def _notification_store() -> NotificationDashboardStore:
    return NotificationDashboardStore(NOTIFICATION_STORAGE_PATH)


def _resolve_dashboard_user_id(request: Request) -> str:
    possible_headers = [
        "x-ha-user-id",
        "x-home-assistant-user-id",
        "x-forwarded-user",
        "remote-user",
    ]
    for header_name in possible_headers:
        value = (request.headers.get(header_name) or "").strip()
        if value:
            return value
    return "default-user"


def _safe_notification_id(user_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "-", (user_id or "").strip())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if not normalized:
        normalized = "default-user"
    return f"dashboard-test-{normalized[:48]}"


def _discover_notification_targets_from_env() -> list[NotificationTargetModel]:
    configured = ""
    for candidate in (Path("/data/options.yaml"), Path("/data/options.json")):
        if candidate.exists():
            configured = candidate.read_text(encoding="utf-8")
            break
    service_names = re.findall(r"mobile_app_[a-zA-Z0-9_]+", configured)
    targets: list[NotificationTargetModel] = []
    seen: set[str] = set()
    for service_name in service_names:
        service = f"notify.{service_name}"
        if service in seen:
            continue
        seen.add(service)
        targets.append(
            NotificationTargetModel(
                id=service,
                service=service,
                display_name=service_name.replace("mobile_app_", "")
                .replace("_", " ")
                .title(),
                platform="ios" if "iphone" in service_name else "android",
                active=True,
            )
        )
    return targets


def _discover_notification_targets_from_homeassistant() -> (
    list[NotificationTargetModel]
):
    supervisor_url = (os.getenv("SUPERVISOR_URL") or "http://supervisor").rstrip("/")
    endpoint_candidates: list[str] = []
    for endpoint in (
        f"{supervisor_url}/core/api/services",
        f"{supervisor_url}/api/services",
    ):
        if endpoint not in endpoint_candidates:
            endpoint_candidates.append(endpoint)

    seen_services: set[str] = set()
    discovered: list[NotificationTargetModel] = []
    for endpoint in endpoint_candidates:
        for headers in _build_homeassistant_auth_headers():
            try:
                response = requests.get(endpoint, headers=headers, timeout=10)
            except requests.RequestException:
                continue

            if response.status_code != 200:
                continue

            try:
                payload = response.json()
            except ValueError:
                continue

            if not isinstance(payload, list):
                continue

            for domain_entry in payload:
                if not isinstance(domain_entry, dict):
                    continue
                if domain_entry.get("domain") != "notify":
                    continue
                services = domain_entry.get("services") or {}
                if not isinstance(services, dict):
                    continue
                for service_name in services.keys():
                    if not isinstance(service_name, str):
                        continue
                    if not service_name.startswith("mobile_app_"):
                        continue
                    full_service = f"notify.{service_name}"
                    if full_service in seen_services:
                        continue
                    seen_services.add(full_service)
                    discovered.append(
                        NotificationTargetModel(
                            id=full_service,
                            service=full_service,
                            display_name=service_name.replace("mobile_app_", "")
                            .replace("_", " ")
                            .title(),
                            platform="ios" if "iphone" in service_name else "android",
                            active=True,
                        )
                    )

            if discovered:
                return discovered

    return discovered


def _load_notification_overview(request: Request) -> NotificationOverviewResponse:
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = store.load_for_user(user_id)
    discovered_targets = _discover_notification_targets_from_homeassistant()
    if not discovered_targets:
        discovered_targets = _discover_notification_targets_from_env()
    if discovered_targets:
        existing_by_id = {item.id: item for item in overview.devices}
        merged_devices: list[NotificationTargetModel] = []
        for discovered in discovered_targets:
            current = existing_by_id.get(discovered.id)
            if current:
                discovered.user_id = current.user_id
                discovered.active = current.active
            elif user_id != "default-user":
                discovered.user_id = user_id
            merged_devices.append(discovered)
        overview.devices = merged_devices
        store.save_overview_for_user(user_id, overview)

    # Global activation is controlled by add-on app options (options.yaml).
    overview.settings.enabled = bool(get_settings().notification_global_enabled)
    return overview


@router.get(
    "/api/dashboard/notifications/overview",
    response_model=NotificationOverviewResponse,
)
def dashboard_notification_overview(
    request: Request,
    _: None = Depends(require_auth),
):
    return _load_notification_overview(request)


@router.put(
    "/api/dashboard/notifications/settings",
    response_model=NotificationSettingsModel,
)
def dashboard_notification_update_settings(
    request: Request,
    payload: NotificationSettingsUpdateRequest,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    update_payload = payload.model_dump()
    update_payload["enabled"] = bool(get_settings().notification_global_enabled)
    overview.settings = NotificationSettingsModel(**update_payload)
    store.save_overview_for_user(user_id, overview)
    return overview.settings


@router.patch(
    "/api/dashboard/notifications/devices/{device_id}",
    response_model=NotificationTargetModel,
)
def dashboard_notification_update_device(
    request: Request,
    device_id: str,
    payload: NotificationDeviceUpdateRequest,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    for device in overview.devices:
        if device.id == device_id:
            device.active = payload.active
            device.user_id = payload.user_id or user_id
            store.save_overview_for_user(user_id, overview)
            return device
    raise HTTPException(status_code=404, detail="Device not found")


@router.post(
    "/api/dashboard/notifications/rules",
    response_model=NotificationRuleModel,
)
def dashboard_notification_create_rule(
    request: Request,
    payload: NotificationRuleUpsertRequest,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    rule = NotificationRuleModel(id=str(uuid4()), **payload.model_dump())
    overview.rules.insert(0, rule)
    store.save_overview_for_user(user_id, overview)
    return rule


@router.patch(
    "/api/dashboard/notifications/rules/{rule_id}",
    response_model=NotificationRuleModel,
)
def dashboard_notification_update_rule(
    request: Request,
    rule_id: str,
    payload: NotificationRuleUpsertRequest,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    for index, rule in enumerate(overview.rules):
        if rule.id == rule_id:
            updated = NotificationRuleModel(id=rule_id, **payload.model_dump())
            overview.rules[index] = updated
            store.save_overview_for_user(user_id, overview)
            return updated
    raise HTTPException(status_code=404, detail="Rule not found")


@router.delete("/api/dashboard/notifications/rules/{rule_id}")
def dashboard_notification_delete_rule(
    request: Request,
    rule_id: str,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    original_count = len(overview.rules)
    overview.rules = [rule for rule in overview.rules if rule.id != rule_id]
    if len(overview.rules) == original_count:
        raise HTTPException(status_code=404, detail="Rule not found")
    store.save_overview_for_user(user_id, overview)
    return {"success": True, "removed_rule_id": rule_id}


@router.post("/api/dashboard/notifications/tests/device")
def dashboard_notification_test_device(
    request: Request,
    payload: NotificationTestRequest,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    target_id = payload.target_id

    selected_device = None
    if target_id:
        selected_device = next(
            (device for device in overview.devices if device.id == target_id),
            None,
        )
        if not selected_device:
            raise HTTPException(status_code=404, detail="Device not found")
    else:
        selected_device = next(
            (device for device in overview.devices if device.active), None
        )

    if not selected_device:
        raise HTTPException(status_code=400, detail="No active device found")

    delivered, error = _send_mobile_notification_to_homeassistant(
        service_id=selected_device.service,
        title="Testbenachrichtigung",
        message=f"Test an {selected_device.display_name}",
        platform_hint=selected_device.platform,
    )
    user_error = _build_mobile_notification_user_error(error)

    overview.history.insert(
        0,
        create_history_entry(
            event_type="shopping_due",
            title="Testbenachrichtigung",
            message=f"Test an {selected_device.display_name}",
            delivered=delivered,
            target_id=selected_device.id,
            channels=["mobile_push"],
            error="" if delivered else user_error,
        ),
    )
    store.save_overview_for_user(user_id, overview)

    if not delivered:
        logger.warning(
            "Mobile Testbenachrichtigung fehlgeschlagen (technisch): %s",
            error or "notify-Service konnte nicht versendet werden",
        )
        raise HTTPException(status_code=502, detail=user_error)

    return {"success": True, "message": "Testbenachrichtigung gesendet."}


@router.post("/api/dashboard/notifications/tests/all")
def dashboard_notification_test_all(
    request: Request,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    active_devices = [device for device in overview.devices if device.active]

    if not active_devices:
        raise HTTPException(status_code=400, detail="No active device found")

    sent_to = 0
    failed_to = 0
    last_error = ""
    for device in active_devices:
        delivered, error = _send_mobile_notification_to_homeassistant(
            service_id=device.service,
            title="Testbenachrichtigung",
            message=f"Test an {device.display_name}",
            platform_hint=device.platform,
        )
        if delivered:
            sent_to += 1
            user_error = ""
        else:
            failed_to += 1
            last_error = error or last_error
            user_error = _build_mobile_notification_user_error(error)

        overview.history.insert(
            0,
            create_history_entry(
                event_type="shopping_due",
                title="Testbenachrichtigung",
                message=f"Test an {device.display_name}",
                delivered=delivered,
                target_id=device.id,
                channels=["mobile_push"],
                error=user_error,
            ),
        )

    store.save_overview_for_user(user_id, overview)

    if sent_to == 0 and failed_to > 0:
        logger.warning(
            "Mobile Testbenachrichtigung an alle Geräte fehlgeschlagen (technisch): %s",
            last_error or "notify-Services konnten nicht versendet werden",
        )
        raise HTTPException(
            status_code=502,
            detail=_build_mobile_notification_user_error(last_error),
        )

    return {"success": True, "sent_to": sent_to, "failed_to": failed_to}


@router.post("/api/dashboard/notifications/tests/persistent")
def dashboard_notification_test_persistent(
    request: Request,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)

    delivered, error = _send_persistent_notification_to_homeassistant(
        title="Testbenachrichtigung",
        message="Test als persistent_notification",
        notification_id=_safe_notification_id(user_id),
    )
    user_error = _build_persistent_notification_user_error(error)
    overview.history.insert(
        0,
        create_history_entry(
            event_type="shopping_due",
            title="Testbenachrichtigung",
            message="Test als persistent_notification",
            delivered=delivered,
            target_id="persistent_notification",
            channels=["persistent_notification"],
            error="" if delivered else user_error,
        ),
    )
    store.save_overview_for_user(user_id, overview)

    if not delivered:
        logger.warning(
            "Persistente Testbenachrichtigung fehlgeschlagen (technisch): %s",
            error or "persistent_notification konnte nicht versendet werden",
        )
        raise HTTPException(
            status_code=502,
            detail=user_error,
        )

    return {"success": True}


@router.post("/api/v1/notifications/test")
def notification_test_v1(
    request: Request,
    _: None = Depends(require_auth),
):
    return dashboard_notification_test_persistent(request, None)


def _normalize_base_path(value: str) -> str:
    normalized_value = (value or "").strip().rstrip("/")
    if not normalized_value:
        return ""
    if not normalized_value.startswith("/"):
        normalized_value = f"/{normalized_value}"
    return normalized_value


def _render_dashboard(settings: Settings, request: Request):
    api_base_path = _normalize_base_path(request.scope.get("root_path") or "")
    ingress_prefix_match = re.match(r"^(/api/hassio_ingress/[^/]+)", request.url.path)
    ingress_prefix = ingress_prefix_match.group(1) if ingress_prefix_match else ""
    token_prefix_match = re.match(r"^(/[^/]+)", request.url.path)
    token_prefix = token_prefix_match.group(1) if token_prefix_match else ""
    header_prefix = _normalize_base_path(request.headers.get("x-ingress-path") or "")
    forwarded_prefix_header = request.headers.get("x-forwarded-prefix") or ""
    forwarded_prefix = _normalize_base_path(forwarded_prefix_header.split(",", 1)[0])

    api_request_base_path = api_base_path or ingress_prefix

    resolved_base_path = api_request_base_path
    if not resolved_base_path:
        resolved_base_path = header_prefix or forwarded_prefix
    if not resolved_base_path and token_prefix not in {"", "/api", "/dashboard-static"}:
        resolved_base_path = token_prefix

    if api_request_base_path == "" and resolved_base_path.startswith(
        "/api/hassio_ingress/"
    ):
        api_request_base_path = resolved_base_path

    static_base_path = (
        f"{resolved_base_path}/dashboard-static"
        if resolved_base_path
        else "/dashboard-static"
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "configured_api_key": settings.api_key,
            "api_base_path": api_request_base_path,
            "static_base_path": static_base_path,
            "scanner_llava_fallback_seconds": settings.scanner_barcode_fallback_seconds,
            "scanner_llava_timeout_seconds": settings.scanner_llava_timeout_seconds,
            "ha_user_id": _resolve_dashboard_user_id(request),
            "dashboard_polling_interval_seconds": settings.dashboard_polling_interval_seconds,
            "theme_source": "home-assistant-parent",
            "theme_bridge_mode": "same-origin-css-vars",
            "theme_var_names": ",".join(
                [
                    "primary-background-color",
                    "secondary-background-color",
                    "card-background-color",
                    "primary-text-color",
                    "secondary-text-color",
                    "divider-color",
                    "primary-color",
                    "error-color",
                    "success-color",
                ]
            ),
        },
    )


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, settings: Settings = Depends(get_settings)):
    return _render_dashboard(settings, request)


@router.get("/{full_path:path}", response_class=HTMLResponse)
def dashboard_fallback(
    full_path: str,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    normalized_path = full_path.strip("/").lower()
    if normalized_path.startswith("api/") and not normalized_path.startswith(
        "api/hassio_ingress/"
    ):
        raise HTTPException(status_code=404, detail="Not Found")

    return _render_dashboard(settings, request)
