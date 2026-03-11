import logging
import re
from base64 import b64encode
from pathlib import Path
from urllib.parse import ParseResult, quote, urljoin, urlparse

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from grocy_ai_assistant.ai.ingredient_detector import IngredientDetector
from grocy_ai_assistant.config.settings import Settings, get_settings
from grocy_ai_assistant.models.ingredient import (
    AnalyzeProductRequest,
    AnalyzeProductResponse,
    DashboardSearchResponse,
    ExistingProductAddRequest,
    LocationResponse,
    ProductVariantResponse,
    RecipeSuggestionItem,
    RecipeSuggestionRequest,
    RecipeSuggestionResponse,
    ShoppingListItemResponse,
    StockProductResponse,
)
from grocy_ai_assistant.services.grocy_client import GrocyClient

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
bearer_auth = HTTPBearer(auto_error=False)


def _maybe_encode_product_picture_path(path: str) -> str:
    if "/productpictures/" not in path:
        return path

    prefix, _, suffix = path.rpartition("/")
    if not suffix or "." not in suffix:
        return path

    encoded_picture_name = b64encode(suffix.encode("utf-8")).decode("ascii")
    return f"{prefix}/{encoded_picture_name}"


def _build_product_picture_url(raw_picture_url: str, settings: Settings) -> str:
    picture_value = (raw_picture_url or "").strip()
    if not picture_value:
        return ""

    if picture_value.startswith("data:"):
        return picture_value

    parsed_grocy_base = urlparse(settings.grocy_base_url.rstrip("/"))
    grocy_base_url = parsed_grocy_base.geturl().rstrip("/")

    if picture_value.startswith(("http://", "https://")):
        parsed_picture = urlparse(picture_value)
        if parsed_picture.hostname in {
            "localhost",
            "127.0.0.1",
            "::1",
            "homeassistant",
        }:
            rewritten_picture = ParseResult(
                scheme=parsed_grocy_base.scheme or parsed_picture.scheme,
                netloc=parsed_grocy_base.netloc or parsed_picture.netloc,
                path=_maybe_encode_product_picture_path(parsed_picture.path),
                params=parsed_picture.params,
                query=parsed_picture.query,
                fragment=parsed_picture.fragment,
            ).geturl()
            logger.info(
                "Produktbild-URL auf konfigurierten Grocy-Host umgeschrieben: %s -> %s",
                picture_value,
                rewritten_picture,
            )
            return rewritten_picture
        return picture_value

    if "/" not in picture_value:
        encoded_picture_name = b64encode(picture_value.encode("utf-8")).decode("ascii")
        picture_value = f"files/productpictures/{encoded_picture_name}"

    picture_value = _maybe_encode_product_picture_path(picture_value)

    if picture_value.startswith("/"):
        return urljoin(f"{grocy_base_url}/", picture_value)

    return f"{grocy_base_url}/{picture_value.lstrip('/')}"


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
        logger.error("Analyse-Fehler: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get(
    "/api/dashboard/search-variants", response_model=list[ProductVariantResponse]
)
def dashboard_search_variants(
    q: str,
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
            ProductVariantResponse(
                id=product.get("id"),
                name=product.get("name") or "Unbekanntes Produkt",
                picture_url=_build_dashboard_picture_proxy_url(
                    product.get("picture_url")
                    or product.get("picture_file_name")
                    or "",
                    settings,
                ),
            )
            for product in matches
            if product.get("id")
        ]
    except Exception as error:
        logger.error("Produktsuche fehlgeschlagen: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post(
    "/api/dashboard/add-existing-product", response_model=DashboardSearchResponse
)
def dashboard_add_existing_product(
    payload: ExistingProductAddRequest,
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    if not settings.grocy_api_key:
        raise HTTPException(
            status_code=500, detail="grocy_api_key fehlt in Add-on Optionen"
        )

    try:
        grocy_client = GrocyClient(settings)
        grocy_client.add_product_to_shopping_list(payload.product_id, amount=1)
        return DashboardSearchResponse(
            success=True,
            action="existing_added",
            message=f"{payload.product_name} wurde zur Einkaufsliste hinzugefügt.",
            product_id=payload.product_id,
        )
    except Exception as error:
        logger.error("Produkt konnte nicht hinzugefügt werden: %s", error)
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
                existing_product.get("id"), amount=1
            )
            return DashboardSearchResponse(
                success=True,
                action="existing_added",
                message=f"{product_name} war vorhanden und wurde zur Einkaufsliste hinzugefügt.",
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
        grocy_client.add_product_to_shopping_list(created_object_id, amount=1)

        return DashboardSearchResponse(
            success=True,
            action="created_and_added",
            message=f"{product_name} wurde neu angelegt und zur Einkaufsliste hinzugefügt.",
            product_id=created_object_id,
        )
    except Exception as error:
        logger.error("Dashboard-Workflow Fehler: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error


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
        logger.error("Netzwerkfehler beim Laden des Produktbilds %s: %s", src, error)
        raise HTTPException(
            status_code=502,
            detail="Produktbild konnte nicht geladen werden",
        ) from error

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        logger.warning(
            "Produktbild nicht gefunden oder nicht erreichbar (%s): %s", src, error
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
                product_name=item.get("product_name") or "Unbekanntes Produkt",
                note=item.get("note") or "",
                picture_url=_build_dashboard_picture_proxy_url(
                    _extract_shopping_item_picture_value(item),
                    settings,
                ),
            )
            for item in items
        ]
    except Exception as error:
        logger.error("Einkaufsliste konnte nicht geladen werden: %s", error)
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
        logger.error("Standorte konnten nicht geladen werden: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/api/dashboard/stock-products", response_model=list[StockProductResponse])
def dashboard_stock_products(
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
        logger.error("Lagerprodukte konnten nicht geladen werden: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post(
    "/api/dashboard/recipe-suggestions", response_model=RecipeSuggestionResponse
)
def dashboard_recipe_suggestions(
    payload: RecipeSuggestionRequest,
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
        
        if not selected_ids:
            selected_products = [product.get("name", "") for product in stock_products]
        else:
            selected_products = [
                product.get("name", "")
                for product in stock_products
                if product.get("id") in selected_ids
            ]
        
        if not selected_products:
            raise HTTPException(
                status_code=400,
                detail="Auswahl enthält keine gültigen Lagerprodukte",
            )

        grocy_recipes_raw = grocy_client.get_recipes()
        scored = []
        for recipe in grocy_recipes_raw:
            score, reason = _score_recipe_match(recipe, selected_products)
            scored.append((score, recipe, reason))

        scored.sort(key=lambda row: (-row[0], str(row[1].get("name") or "").casefold()))
        grocy_recipes = [
            RecipeSuggestionItem(
                title=str(recipe.get("name") or "Unbenanntes Rezept"),
                source="grocy",
                reason=reason,
            )
            for _, recipe, reason in scored[:5]
        ]

        detector = IngredientDetector(settings)
        ai_raw = detector.generate_recipe_suggestions(
            selected_products,
            [item.title for item in grocy_recipes],
        )
        ai_recipes = [
            RecipeSuggestionItem(
                title=str(item.get("title") or "KI-Rezept"),
                source="ai",
                reason=str(item.get("reason") or ""),
            )
            for item in ai_raw[:5]
            if isinstance(item, dict)
        ]

        return RecipeSuggestionResponse(
            selected_products=selected_products,
            grocy_recipes=grocy_recipes,
            ai_recipes=ai_recipes,
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Rezeptvorschläge konnten nicht erzeugt werden: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.delete("/api/dashboard/shopping-list/clear")
def dashboard_clear_shopping_list(
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
        logger.error("Einkaufsliste konnte nicht geleert werden: %s", error)
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

    resolved_base_path = api_base_path or ingress_prefix
    if not resolved_base_path:
        resolved_base_path = header_prefix or forwarded_prefix
    if not resolved_base_path and token_prefix not in {"", "/api", "/dashboard-static"}:
        resolved_base_path = token_prefix

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
            "api_base_path": api_base_path,
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
