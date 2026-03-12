import logging
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from grocy_ai_assistant.ai.ingredient_detector import IngredientDetector
from grocy_ai_assistant.api.errors import log_api_error
from grocy_ai_assistant.config.settings import Settings, get_settings
from grocy_ai_assistant.core.picture_urls import build_product_picture_url
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
    StockProductResponse,
)
from grocy_ai_assistant.services.grocy_client import GrocyClient

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
bearer_auth = HTTPBearer(auto_error=False)


def _build_product_picture_url(raw_picture_url: str, settings: Settings) -> str:
    rewritten = build_product_picture_url(raw_picture_url, settings)
    if rewritten and rewritten != (raw_picture_url or ""):
        logger.info(
            "Produktbild-URL auf konfigurierten Grocy-Host umgeschrieben: %s -> %s",
            raw_picture_url,
            rewritten,
        )
    return rewritten


def _build_dashboard_picture_proxy_url(raw_picture_url: str, settings: Settings) -> str:
    absolute_picture_url = _build_product_picture_url(raw_picture_url, settings)
    if not absolute_picture_url:
        return ""

    return f"/api/dashboard/product-picture?src={quote(absolute_picture_url, safe='')}"


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
    for _, recipe, reason in scored[:5]:
        recipe_id = (
            int(recipe.get("id")) if str(recipe.get("id") or "").isdigit() else None
        )
        missing_products = (
            grocy_client.get_missing_recipe_products(recipe_id)
            if recipe_id is not None
            else []
        )
        grocy_recipes.append(
            RecipeSuggestionItem(
                recipe_id=recipe_id,
                title=str(recipe.get("name") or "Unbenanntes Rezept"),
                source="grocy",
                reason=reason,
                preparation=str(recipe.get("description") or ""),
                picture_url=str(recipe.get("picture_url") or ""),
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
        ai_raw = [
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
        ]

    ai_recipes: list[RecipeSuggestionItem] = []
    for item in ai_raw[:5]:
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

        ai_recipes.append(
            RecipeSuggestionItem(
                title=str(item.get("title") or "KI-Rezept"),
                source="ai",
                reason=str(item.get("reason") or ""),
                preparation=str(item.get("preparation") or ""),
                ingredients=normalized_ingredients,
                picture_url="",
            )
        )

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
    return {
        "location_ids": [],
        "stock_signature": _build_stock_signature(stock_products),
        "response": payload,
    }


def _variant_from_grocy_product(
    product: dict, settings: Settings
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
    detector: IngredientDetector,
    settings: Settings,
) -> list[ProductVariantResponse]:
    variants: list[ProductVariantResponse] = []
    seen_names: set[str] = set()

    for product in grocy_client.search_products_by_partial_name(product_name):
        variant = _variant_from_grocy_product(product, settings)
        normalized_name = variant.name.casefold()
        if normalized_name in seen_names:
            continue
        variants.append(variant)
        seen_names.add(normalized_name)

    ai_suggestions = detector.suggest_similar_products(product_name)
    for item in ai_suggestions:
        suggested_name = str(item.get("name") or "").strip()
        if not suggested_name:
            continue

        for product in grocy_client.search_products_by_partial_name(suggested_name):
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

    return variants[:10]


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


@router.get("/api/status")
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
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    query = q.strip()
    if not query:
        return []

    try:
        grocy_client = GrocyClient(settings)
        matches = grocy_client.search_products_by_partial_name(query)
        return [
            _variant_from_grocy_product(product, settings)
            for product in matches
            if product.get("id")
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
        grocy_client.add_product_to_shopping_list(
            payload.product_id,
            amount=payload.amount,
            best_before_date=payload.best_before_date,
        )
        return DashboardSearchResponse(
            success=True,
            action="existing_added",
            message=f"{payload.product_name} wurde zur Einkaufsliste hinzugefügt.",
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

    product_name = payload.name.strip()
    if not product_name:
        raise HTTPException(status_code=400, detail="Bitte Produktname eingeben")

    detector = IngredientDetector(settings)
    grocy_client = GrocyClient(settings)

    try:
        existing_product = grocy_client.find_product_by_name(product_name)
        if existing_product:
            grocy_client.add_product_to_shopping_list(
                existing_product.get("id"),
                amount=payload.amount,
                best_before_date=payload.best_before_date,
            )
            return DashboardSearchResponse(
                success=True,
                action="existing_added",
                message=f"{product_name} war vorhanden und wurde zur Einkaufsliste hinzugefügt.",
            )

        fallback_variants = _build_fallback_variants(
            product_name=product_name,
            grocy_client=grocy_client,
            detector=detector,
            settings=settings,
        )
        if fallback_variants:
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
        created_object_id = grocy_client.create_product(product_data)
        grocy_client.add_product_to_shopping_list(
            created_object_id,
            amount=payload.amount,
            best_before_date=payload.best_before_date,
        )

        return DashboardSearchResponse(
            success=True,
            action="created_and_added",
            message=f"{product_name} wurde neu angelegt und zur Einkaufsliste hinzugefügt.",
            product_id=created_object_id,
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


@router.get("/api/dashboard/barcode/{barcode}", response_model=BarcodeProductResponse)
def dashboard_barcode_lookup(
    barcode: str,
    request: Request,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    normalized_barcode = "".join(ch for ch in barcode if ch.isdigit())
    if len(normalized_barcode) < 8:
        raise HTTPException(status_code=400, detail="Ungültiger Barcode")

    grocy_client = GrocyClient(settings)

    try:
        response = requests.get(
            f"https://world.openfoodfacts.org/api/v2/product/{normalized_barcode}.json",
            timeout=8,
            headers={"User-Agent": "grocy-ai-assistant/scan-tab"},
        )
        payload = response.json()
        product = payload.get("product") if isinstance(payload, dict) else {}

        if response.status_code != 200 or int(payload.get("status", 0)) != 1:
            grocy_product = grocy_client.find_product_by_barcode(normalized_barcode)
            if grocy_product:
                return BarcodeProductResponse(
                    barcode=normalized_barcode,
                    found=True,
                    product_name=str(grocy_product.get("name") or ""),
                    source="Grocy",
                )

            return BarcodeProductResponse(
                barcode=normalized_barcode,
                found=False,
            )

        return BarcodeProductResponse(
            barcode=normalized_barcode,
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
    except requests.RequestException:
        grocy_product = grocy_client.find_product_by_barcode(normalized_barcode)
        if grocy_product:
            return BarcodeProductResponse(
                barcode=normalized_barcode,
                found=True,
                product_name=str(grocy_product.get("name") or ""),
                source="Grocy",
            )
        raise
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


@router.get("/api/dashboard/product-picture")
def dashboard_product_picture(
    src: str,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    if not src:
        raise HTTPException(status_code=400, detail="Bildquelle fehlt")

    parsed_src = urlparse(src)
    parsed_grocy = urlparse(settings.grocy_base_url)
    if (
        parsed_src.scheme not in ("http", "https")
        or parsed_src.netloc != parsed_grocy.netloc
    ):
        raise HTTPException(status_code=400, detail="Ungültige Bildquelle")

    image_cache = _get_product_image_cache(request)
    if image_cache:
        cached_content, cached_media_type = image_cache.get_cached_image(src)
        if cached_content is not None:
            return Response(content=cached_content, media_type=cached_media_type)

    logger.info("Lade Produktbild via Proxy: %s", src)
    try:
        response = requests.get(
            src,
            headers={"GROCY-API-KEY": settings.grocy_api_key},
            timeout=30,
        )
    except requests.RequestException as error:
        log_api_error(
            logger,
            request=request,
            status_code=502,
            message="Produktbild konnte nicht geladen werden",
            details=[{"source": src}],
            exc=error,
        )
        raise HTTPException(
            status_code=502,
            detail="Produktbild konnte nicht geladen werden",
        ) from error

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        log_api_error(
            logger,
            request=request,
            status_code=404,
            message="Bild nicht gefunden",
            details=[{"source": src}],
            exc=error,
        )
        raise HTTPException(status_code=404, detail="Bild nicht gefunden") from error

    content_type = response.headers.get("Content-Type", "image/jpeg")
    return Response(content=response.content, media_type=content_type)


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
        stock_products = (
            grocy_client.get_stock_products(selected_location_ids)
            if selected_location_ids
            else grocy_client.get_stock_products()
        )
        return [StockProductResponse(**item) for item in stock_products]
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
                product_id = entry.get("product_id")
                if not isinstance(product_id, int):
                    continue

                best_before_raw = str(
                    entry.get("best_before_date")
                    or entry.get("best_before_date_calculated")
                    or ""
                ).strip()
                if not best_before_raw:
                    continue

                try:
                    best_before = date.fromisoformat(best_before_raw)
                except ValueError:
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

        if (
            not payload.location_ids
            and not selected_ids
            and not payload.soon_expiring_only
        ):
            cache = _get_recipe_suggestion_cache(request)
            stock_signature = _build_stock_signature(stock_products)
            if cache:
                cached_payload = cache.get("response")
                if cache.get("stock_signature") == stock_signature and cached_payload:
                    logger.info(
                        "Nutze initialen Rezeptvorschlags-Cache (Bestand unverändert)"
                    )
                    return RecipeSuggestionResponse(**cached_payload)

        response = _generate_recipe_suggestions(
            stock_products=stock_products,
            selected_ids=selected_ids,
            grocy_client=grocy_client,
            settings=settings,
        )

        if (
            not payload.location_ids
            and not selected_ids
            and not payload.soon_expiring_only
        ):
            cache = _get_recipe_suggestion_cache(request)
            if cache is not None:
                cache["location_ids"] = []
                cache["stock_signature"] = _build_stock_signature(stock_products)
                cache["response"] = (
                    response.model_dump()
                    if hasattr(response, "model_dump")
                    else response.dict()
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

        grocy_client.complete_shopping_list_item(
            shopping_list_id,
            product_id=int(product_id),
            amount=str(selected_item.get("amount") or "1"),
            best_before_date=str(selected_item.get("best_before_date") or ""),
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
