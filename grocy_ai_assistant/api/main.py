import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from ipaddress import ip_address
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from grocy_ai_assistant.api.errors import build_error_response, log_api_error
from grocy_ai_assistant.api.routes import prefetch_initial_recipe_suggestions, router
from grocy_ai_assistant.ai.ingredient_detector import IngredientDetector
from grocy_ai_assistant.config.settings import Settings, get_settings
from grocy_ai_assistant.services.grocy_client import GrocyClient
from grocy_ai_assistant.services.location_cache import LocationCache
from grocy_ai_assistant.services.product_image_cache import ProductImageCache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _as_float_or_none(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _generate_missing_product_images_on_startup(settings: Settings) -> None:
    if not settings.generate_missing_product_images_on_startup:
        return

    if not settings.image_generation_enabled:
        logger.info(
            "Batch-Bildgenerierung beim Start übersprungen: image_generation_enabled ist deaktiviert"
        )
        return

    client = GrocyClient(settings)
    detector = IngredientDetector(settings)

    try:
        products_without_picture = client.get_products_without_picture()
    except Exception as error:
        logger.warning("Produkte ohne Bild konnten nicht geladen werden: %s", error)
        return

    if not products_without_picture:
        logger.info(
            "Batch-Bildgenerierung beim Start: Keine Produkte ohne Bild gefunden"
        )
        return

    logger.info(
        "Batch-Bildgenerierung beim Start gestartet für %s Produkte ohne Bild",
        len(products_without_picture),
    )

    generated_count = 0
    for product in products_without_picture:
        product_name = str(product.get("name") or "").strip()
        raw_product_id = product.get("id")
        try:
            product_id = int(raw_product_id)
        except (TypeError, ValueError):
            continue

        if not product_name:
            continue

        try:
            image_path = detector.generate_product_image(product_name)
            if not image_path:
                continue
            client.attach_product_picture(product_id, image_path)
            generated_count += 1
        except Exception as error:
            logger.warning(
                "Produktbild konnte im Startup-Batch nicht erstellt/gespeichert werden (%s): %s",
                product_name,
                error,
            )

    logger.info(
        "Batch-Bildgenerierung beim Start abgeschlossen: %s von %s Produkten aktualisiert",
        generated_count,
        len(products_without_picture),
    )


def _run_initial_info_sync_on_startup(settings: Settings) -> None:
    if not settings.initial_info_sync:
        return

    client = GrocyClient(settings)
    detector = IngredientDetector(settings)

    try:
        products = client.get_products()
    except Exception as error:
        logger.warning("Initialer Info-Sync konnte Produkte nicht laden: %s", error)
        return

    if not products:
        logger.info("Initialer Info-Sync: Keine Produkte gefunden")
        return

    logger.info(
        "Initialer Info-Sync gestartet: %s Produkte aus Grocy geladen",
        len(products),
    )

    synced_count = 0
    considered_count = 0

    for product in products:
        product_name = str(product.get("name") or "").strip()
        product_id_raw = product.get("id")
        try:
            product_id = int(product_id_raw)
        except (TypeError, ValueError):
            continue

        if not product_name:
            continue

        if settings.debug_mode:
            logger.debug(
                "Initialer Info-Sync: Prüfe Produkt id=%s name=%s",
                product_id,
                product_name,
            )

        try:
            nutrition = client.get_product_nutrition(product_id)
        except Exception as error:
            logger.warning(
                "Initialer Info-Sync: Nährwerte für Produkt %s konnten nicht geladen werden: %s",
                product_id,
                error,
            )
            continue

        missing_calories = not _as_float_or_none(nutrition.get("calories"))
        missing_carbs = not _as_float_or_none(nutrition.get("carbs"))
        missing_fat = not _as_float_or_none(nutrition.get("fat"))
        missing_protein = not _as_float_or_none(nutrition.get("protein"))
        missing_sugar = not _as_float_or_none(nutrition.get("sugar"))
        missing_best_before_days = not _as_float_or_none(
            product.get("default_best_before_days")
        )

        if not any(
            [
                missing_calories,
                missing_carbs,
                missing_fat,
                missing_protein,
                missing_sugar,
                missing_best_before_days,
            ]
        ):
            if settings.debug_mode:
                logger.debug(
                    "Initialer Info-Sync: Produkt %s hat keine fehlenden Felder",
                    product_id,
                )
            continue

        considered_count += 1

        try:
            ai_data = detector.analyze_product_name(product_name)
        except Exception as error:
            logger.warning(
                "Initialer Info-Sync: KI-Analyse fehlgeschlagen für Produkt %s (%s): %s",
                product_id,
                product_name,
                error,
            )
            continue

        calories = (
            _as_float_or_none(ai_data.get("calories")) if missing_calories else None
        )
        carbs = (
            _as_float_or_none(ai_data.get("carbohydrates")) if missing_carbs else None
        )
        fat = _as_float_or_none(ai_data.get("fat")) if missing_fat else None
        protein = _as_float_or_none(ai_data.get("protein")) if missing_protein else None
        sugar = _as_float_or_none(ai_data.get("sugar")) if missing_sugar else None
        best_before_days = (
            int(_as_float_or_none(ai_data.get("default_best_before_days")) or 0)
            if missing_best_before_days
            else 0
        )

        if not any(
            value and value > 0
            for value in [calories, carbs, fat, protein, sugar, best_before_days]
        ):
            if settings.debug_mode:
                logger.debug(
                    "Initialer Info-Sync: Produkt %s lieferte keine verwertbaren KI-Werte",
                    product_id,
                )
            continue

        try:
            client.update_product_nutrition(
                product_id=product_id,
                calories=calories if calories and calories > 0 else None,
                carbs=carbs if carbs and carbs > 0 else None,
                fat=fat if fat and fat > 0 else None,
                protein=protein if protein and protein > 0 else None,
                sugar=sugar if sugar and sugar > 0 else None,
            )
            if best_before_days > 0:
                client.set_product_default_best_before_days(
                    product_id, best_before_days
                )
            synced_count += 1
        except Exception as error:
            logger.warning(
                "Initialer Info-Sync: Produkt %s konnte nicht aktualisiert werden: %s",
                product_id,
                error,
            )

    logger.info(
        "Initialer Info-Sync abgeschlossen: %s von %s Produkten aktualisiert",
        synced_count,
        considered_count,
    )


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = get_settings()
    image_cache = ProductImageCache(settings)
    location_cache = LocationCache(settings)
    image_cache.start()
    location_cache.start()
    app.state.product_image_cache = image_cache
    app.state.location_cache = location_cache
    app.state.recipe_suggestion_cache = {}

    async def _delayed_prefetch_recipe_suggestions() -> None:
        await asyncio.sleep(5)
        try:
            prefetched = await asyncio.to_thread(
                prefetch_initial_recipe_suggestions, settings
            )
            if prefetched:
                app.state.recipe_suggestion_cache.update(prefetched)
                logger.info(
                    "Initiale Rezeptvorschläge zeitverzögert vorab geladen und gecacht"
                )

            await asyncio.to_thread(_generate_missing_product_images_on_startup, settings)

            image_sync_completed = await asyncio.to_thread(
                image_cache.wait_for_initial_refresh, 120.0
            )
            if image_sync_completed:
                logger.info(
                    "Startup-Bildsync abgeschlossen, starte initialen Info-Sync"
                )
            else:
                logger.warning(
                    "Startup-Bildsync nicht innerhalb von 120 Sekunden abgeschlossen; initialer Info-Sync startet trotzdem"
                )

            await asyncio.to_thread(_run_initial_info_sync_on_startup, settings)
        except Exception as error:
            logger.warning(
                "Zeitverzögertes Vorladen der Rezeptvorschläge fehlgeschlagen: %s",
                error,
            )

    prefetch_task = asyncio.create_task(_delayed_prefetch_recipe_suggestions())

    try:
        yield
    finally:
        prefetch_task.cancel()
        image_cache.stop()
        location_cache.stop()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_instance = FastAPI(title="Grocy AI Assistant API", lifespan=_lifespan)
    app_instance.mount(
        "/dashboard-static",
        StaticFiles(directory=str(Path(__file__).parent / "static")),
        name="dashboard_static",
    )
    app_instance.include_router(router)

    @app_instance.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return build_error_response(
            request,
            status_code=exc.status_code,
            message=str(exc.detail),
        )

    @app_instance.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        validation_details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", [])),
                "message": error.get("msg", "Ungültige Eingabe"),
            }
            for error in exc.errors()
        ]
        return build_error_response(
            request,
            status_code=422,
            message="Ungültige Anfrageparameter",
            code="validation_error",
            details=validation_details,
        )

    @app_instance.exception_handler(Exception)
    async def handle_unexpected_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        log_api_error(
            logger,
            request=request,
            status_code=500,
            message="Interner Serverfehler",
            exc=exc,
        )
        return build_error_response(
            request,
            status_code=500,
            message="Interner Serverfehler",
        )

    @app_instance.middleware("http")
    async def enforce_https_for_external_requests(request: Request, call_next):
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        host = request.headers.get("x-forwarded-host") or request.headers.get(
            "host", ""
        )
        scheme_is_http = request.url.scheme == "http" and forwarded_proto != "https"

        if scheme_is_http and _is_external_host(host):
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=307)

        return await call_next(request)

    @app_instance.middleware("http")
    async def log_request_info(request: Request, call_next):
        is_status_check = request.method == "GET" and request.url.path == "/api/status"
        start_time = time.perf_counter()
        if not is_status_check:
            logger.info(
                "Anfrage erhalten: method=%s path=%s query=%s client=%s",
                request.method,
                request.url.path,
                request.url.query,
                request.client.host if request.client else "unknown",
            )

        response = await call_next(request)

        if not is_status_check:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Antwort gesendet: method=%s path=%s status=%s dauer_ms=%.1f",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
        return response

    return app_instance


def _is_external_host(host: str) -> bool:
    normalized_host = (host or "").split(":", 1)[0].strip("[]").lower()
    if not normalized_host:
        return False
    if normalized_host in {"localhost", "::1"}:
        return False
    if normalized_host.endswith(".local"):
        return False
    try:
        parsed_ip = ip_address(normalized_host)
        return not (
            parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local
        )
    except ValueError:
        return True


app = create_app()

if __name__ == "__main__":
    print(">>> GROCY AI ENGINE GESTARTET AUF PORT 8000 <<<", flush=True)
    uvicorn.run("grocy_ai_assistant.api.main:app", host="0.0.0.0", port=8000)
