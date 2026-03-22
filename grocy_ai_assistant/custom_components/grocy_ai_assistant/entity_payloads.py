"""Payload helpers for Home Assistant entities."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

DEFAULT_EXPIRING_WITHIN_DAYS = 3


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_date(value: Any) -> date | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None

    candidate = raw_value[:10]
    try:
        return date.fromisoformat(candidate)
    except ValueError:
        return None


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _select_top_recipe(
    payload: dict[str, Any],
    *,
    source: str | None = None,
) -> dict[str, Any] | None:
    grocy_recipes = [dict(recipe) for recipe in payload.get("grocy_recipes") or []]
    ai_recipes = [dict(recipe) for recipe in payload.get("ai_recipes") or []]
    recipes = [*grocy_recipes, *ai_recipes]
    if source:
        normalized_source = source.strip().casefold()
        recipes = [
            recipe
            for recipe in recipes
            if str(recipe.get("source") or "").strip().casefold() == normalized_source
        ]

    for recipe in recipes:
        title = str(recipe.get("title") or "").strip()
        if title:
            return recipe
    return None


def build_shopping_list_summary(
    items: list[dict[str, Any]],
) -> tuple[int, dict[str, Any]]:
    normalized_items = [dict(item) for item in items]
    locations = _sorted_unique(
        [str(item.get("location_name") or "").strip() for item in normalized_items]
    )
    next_best_before = min(
        (
            best_before.isoformat()
            for best_before in (
                _parse_date(item.get("best_before_date")) for item in normalized_items
            )
            if best_before is not None
        ),
        default="",
    )
    return len(normalized_items), {
        "items": normalized_items,
        "locations": locations,
        "next_best_before_date": next_best_before,
        "updated_at": _utc_now_iso(),
    }


def build_stock_summary(products: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    normalized_products = [dict(product) for product in products]
    locations = _sorted_unique(
        [
            str(product.get("location_name") or "").strip()
            for product in normalized_products
        ]
    )
    return len(normalized_products), {
        "products": normalized_products,
        "locations": locations,
        "updated_at": _utc_now_iso(),
    }


def build_expiring_stock_summary(
    products: list[dict[str, Any]],
    *,
    expiring_within_days: int = DEFAULT_EXPIRING_WITHIN_DAYS,
    today: date | None = None,
) -> tuple[int, dict[str, Any]]:
    normalized_products = [dict(product) for product in products]
    today = today or date.today()
    deadline = today + timedelta(days=max(1, int(expiring_within_days)))

    expiring_products: list[dict[str, Any]] = []
    for product in normalized_products:
        best_before = _parse_date(product.get("best_before_date"))
        if best_before is None:
            continue
        if today <= best_before <= deadline:
            product_payload = dict(product)
            product_payload["days_until_best_before"] = (best_before - today).days
            expiring_products.append(product_payload)

    expiring_products.sort(
        key=lambda item: (
            item.get("best_before_date") or "9999-99-99",
            str(item.get("name") or "").casefold(),
        )
    )

    next_best_before = (
        str(expiring_products[0].get("best_before_date") or "")
        if expiring_products
        else ""
    )
    return len(expiring_products), {
        "products": expiring_products,
        "expiring_within_days": max(1, int(expiring_within_days)),
        "next_best_before_date": next_best_before,
        "updated_at": _utc_now_iso(),
    }


def build_recipe_summary(
    payload: dict[str, Any],
    *,
    soon_expiring_only: bool,
    expiring_within_days: int = DEFAULT_EXPIRING_WITHIN_DAYS,
    source: str | None = None,
) -> tuple[str, dict[str, Any]]:
    top_recipe = _select_top_recipe(payload, source=source)
    state = (
        str(top_recipe.get("title") or "Keine Vorschläge")
        if top_recipe
        else "Keine Vorschläge"
    )
    grocy_recipes = [dict(recipe) for recipe in payload.get("grocy_recipes") or []]
    ai_recipes = [dict(recipe) for recipe in payload.get("ai_recipes") or []]
    if source:
        normalized_source = source.strip().casefold()
        if normalized_source == "grocy":
            ai_recipes = []
            grocy_recipes = grocy_recipes[:1] if top_recipe else []
        elif normalized_source == "ai":
            grocy_recipes = []
            ai_recipes = ai_recipes[:1] if top_recipe else []

    return state, {
        "soon_expiring_only": soon_expiring_only,
        "expiring_within_days": max(1, int(expiring_within_days)),
        "source": source or "",
        "selected_products": list(payload.get("selected_products") or []),
        "top_recipe": dict(top_recipe) if top_recipe else {},
        "grocy_recipes": grocy_recipes,
        "ai_recipes": ai_recipes,
        "recipes_count": len(grocy_recipes) + len(ai_recipes),
        "updated_at": _utc_now_iso(),
    }


def build_analysis_status_payload(
    *,
    query: str,
    payload: dict[str, Any],
    duration_ms: float | None = None,
) -> tuple[str, dict[str, Any]]:
    http_status = payload.get("_http_status")
    success = bool(payload.get("success", http_status == 200))
    state = "Erfolgreich" if success and http_status == 200 else "Fehler"
    attributes = {
        "query": query,
        "success": success,
        "action": str(payload.get("action") or ""),
        "message": str(payload.get("message") or ""),
        "product_id": payload.get("product_id"),
        "variants": [dict(variant) for variant in payload.get("variants") or []],
        "source": "dashboard_search",
        "http_status": http_status,
        "updated_at": _utc_now_iso(),
    }
    if duration_ms is not None:
        attributes["duration_ms"] = round(float(duration_ms), 1)
    return state, attributes


def build_barcode_status_payload(
    *,
    barcode: str,
    payload: dict[str, Any],
    duration_ms: float | None = None,
) -> tuple[str, dict[str, Any]]:
    found = bool(payload.get("found"))
    state = "Treffer" if found else "Kein Treffer"
    attributes = {
        "barcode": barcode,
        "found": found,
        "product_name": str(payload.get("product_name") or ""),
        "brand": str(payload.get("brand") or ""),
        "quantity": str(payload.get("quantity") or ""),
        "ingredients_text": str(payload.get("ingredients_text") or ""),
        "nutrition_grade": str(payload.get("nutrition_grade") or ""),
        "source": str(payload.get("source") or ""),
        "http_status": payload.get("_http_status"),
        "updated_at": _utc_now_iso(),
    }
    if duration_ms is not None:
        attributes["duration_ms"] = round(float(duration_ms), 1)
    return state, attributes


def build_llava_status_payload(
    *,
    payload: dict[str, Any],
    duration_ms: float | None = None,
) -> tuple[str, dict[str, Any]]:
    success = bool(payload.get("success"))
    state = "Erfolgreich" if success else "Kein Ergebnis"
    attributes = {
        "success": success,
        "product_name": str(payload.get("product_name") or ""),
        "brand": str(payload.get("brand") or ""),
        "hint": str(payload.get("hint") or ""),
        "source": str(payload.get("source") or ""),
        "http_status": payload.get("_http_status"),
        "updated_at": _utc_now_iso(),
    }
    if duration_ms is not None:
        attributes["duration_ms"] = round(float(duration_ms), 1)
    return state, attributes


def build_error_status_payload(
    *,
    source: str,
    error: Exception | str,
    extra: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    attributes = {
        "source": source,
        "error": str(error),
        "updated_at": _utc_now_iso(),
    }
    if extra:
        attributes.update(extra)
    return "Fehler", attributes
