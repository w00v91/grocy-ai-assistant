import logging
import sys
import time
from contextlib import asynccontextmanager
from ipaddress import ip_address
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from grocy_ai_assistant.api.routes import router
from grocy_ai_assistant.config.settings import get_settings
from grocy_ai_assistant.services.location_cache import LocationCache
from grocy_ai_assistant.services.product_image_cache import ProductImageCache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = get_settings()
    image_cache = ProductImageCache(settings)
    location_cache = LocationCache(settings)
    image_cache.start()
    location_cache.start()
    app.state.product_image_cache = image_cache
    app.state.location_cache = location_cache
    try:
        yield
    finally:
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
