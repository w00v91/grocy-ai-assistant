import logging
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import ParseResult, quote, unquote, urlparse
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
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
    ScannerLlavaRequest,
    ScannerLlavaResponse,
    StockProductConsumeRequest,
    StockProductResponse,
    StockProductUpdateRequest,
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

    query, _ = _extract_amount_prefixed_product_input(q)
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

    product_name, parsed_amount = _extract_amount_prefixed_product_input(payload.name)
    if not product_name:
        raise HTTPException(status_code=400, detail="Bitte Produktname eingeben")

    amount = parsed_amount if parsed_amount is not None else payload.amount

    detector = IngredientDetector(settings)
    grocy_client = GrocyClient(settings)

    try:
        existing_product = grocy_client.find_product_by_name(product_name)
        if existing_product:
            grocy_client.add_product_to_shopping_list(
                existing_product.get("id"),
                amount=amount,
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
            amount=amount,
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
    except requests.RequestException as error:
        logger.warning(
            "OpenFoodFacts lookup failed for barcode %s: %s",
            normalized_barcode,
            error,
        )
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

    detector = IngredientDetector(settings)
    try:
        detection = detector.detect_product_from_image(image_base64)
        if not any(detection.values()):
            return ScannerLlavaResponse(success=False)

        return ScannerLlavaResponse(
            success=True,
            product_name=detection.get("product_name", ""),
            brand=detection.get("brand", ""),
            hint=detection.get("hint", ""),
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
            status_code=500, detail="LLaVA-Erkennung konnte nicht durchgeführt werden"
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

    src = _normalize_dashboard_picture_source_url(src)

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

    parsed_src = urlparse(src)
    candidate_urls = [src]
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


@router.post("/api/dashboard/stock-products/{stock_id}/consume")
def dashboard_consume_stock_product(
    stock_id: int,
    payload: StockProductConsumeRequest,
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
        stock_entries = grocy_client.get_stock_entries()
        matched_entry = next(
            (
                entry
                for entry in stock_entries
                if int(entry.get("stock_id") or entry.get("id") or 0) == stock_id
            ),
            None,
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
            stock_id=stock_id,
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


@router.put("/api/dashboard/stock-products/{stock_id}")
def dashboard_update_stock_product(
    stock_id: int,
    payload: StockProductUpdateRequest,
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
        grocy_client.update_stock_entry(
            stock_id=stock_id,
            amount=payload.amount,
            best_before_date=payload.best_before_date,
        )
        return {"success": True, "message": "Bestandseintrag wurde aktualisiert."}
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


def _discover_notification_targets_from_env() -> list[NotificationTargetModel]:
    configured = (
        Path("/data/options.json").read_text(encoding="utf-8")
        if Path("/data/options.json").exists()
        else ""
    )
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


def _load_notification_overview(request: Request) -> NotificationOverviewResponse:
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = store.load_for_user(user_id)
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

    # Global activation is controlled by add-on app options (options.json).
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
    if target_id and not any(device.id == target_id for device in overview.devices):
        raise HTTPException(status_code=404, detail="Device not found")

    entry = create_history_entry(
        event_type="shopping_due",
        title="Testbenachrichtigung",
        message=f"Test an {target_id or 'aktives Gerät'}",
        delivered=True,
        target_id=target_id,
        channels=["mobile_push"],
    )
    overview.history.insert(0, entry)
    store.save_overview_for_user(user_id, overview)
    return {"success": True, "message": "Testbenachrichtigung protokolliert."}


@router.post("/api/dashboard/notifications/tests/all")
def dashboard_notification_test_all(
    request: Request,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    active_devices = [device for device in overview.devices if device.active]
    for device in active_devices:
        overview.history.insert(
            0,
            create_history_entry(
                event_type="shopping_due",
                title="Testbenachrichtigung",
                message=f"Test an {device.display_name}",
                delivered=True,
                target_id=device.id,
                channels=["mobile_push"],
            ),
        )
    store.save_overview_for_user(user_id, overview)
    return {"success": True, "sent_to": len(active_devices)}


@router.post("/api/dashboard/notifications/tests/persistent")
def dashboard_notification_test_persistent(
    request: Request,
    _: None = Depends(require_auth),
):
    store = _notification_store()
    user_id = _resolve_dashboard_user_id(request)
    overview = _load_notification_overview(request)
    overview.history.insert(
        0,
        create_history_entry(
            event_type="shopping_due",
            title="Testbenachrichtigung",
            message="Test als persistent_notification",
            delivered=True,
            target_id="persistent_notification",
            channels=["persistent_notification"],
        ),
    )
    store.save_overview_for_user(user_id, overview)
    return {"success": True}


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
            "ha_user_id": _resolve_dashboard_user_id(request),
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
