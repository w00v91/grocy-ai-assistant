import json
import logging
from urllib.parse import ParseResult, quote, urljoin, urlparse

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from grocy_ai_assistant.ai.ingredient_detector import IngredientDetector
from grocy_ai_assistant.config.settings import Settings, get_settings
from grocy_ai_assistant.models.ingredient import (
    AnalyzeProductRequest,
    AnalyzeProductResponse,
    DashboardSearchResponse,
    ExistingProductAddRequest,
    ProductVariantResponse,
    ShoppingListItemResponse,
)
from grocy_ai_assistant.services.grocy_client import GrocyClient

logger = logging.getLogger(__name__)
router = APIRouter()
bearer_auth = HTTPBearer(auto_error=False)


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
                path=parsed_picture.path,
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
        picture_value = f"files/productpictures/{picture_value}"

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


def _get_product_image_cache(request: Request):
    return getattr(request.app.state, "product_image_cache", None)


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
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    detector = IngredientDetector(settings)
    try:
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


def _render_dashboard(settings: Settings, request: Request) -> str:
    configured_api_key = json.dumps(settings.api_key)
    api_base_path = json.dumps((request.scope.get("root_path") or "").rstrip("/"))
    return r"""
<!doctype html>
<html lang='de'>
  <head>
    <meta charset='utf-8' />
    <meta name='viewport' content='width=device-width,initial-scale=1' />
    <title>Grocy AI Dashboard</title>
    <style>
      :root {
        color-scheme: light;
        --bg-gradient: linear-gradient(140deg, #f3f6ff 0%, #f6fbf8 55%, #ecf4ff 100%);
        --text: #1f2937;
        --card-bg: rgba(255, 255, 255, 0.86);
        --card-border: #dbe6ff;
        --item-bg: #fff;
        --item-border: #e6ecff;
        --muted: #5f6d85;
        --input-border: #cad6f8;
        --badge-bg: #edf2ff;
        --badge-text: #3555ad;
        --image-bg: #eef2f9;
      }
      :root[data-theme='dark'] {
        color-scheme: dark;
        --bg-gradient: linear-gradient(140deg, #0f172a 0%, #0b1a21 55%, #111827 100%);
        --text: #e5ecff;
        --card-bg: rgba(20, 32, 58, 0.88);
        --card-border: #334155;
        --item-bg: #172036;
        --item-border: #304263;
        --muted: #a7b6d4;
        --input-border: #42587f;
        --badge-bg: #273a63;
        --badge-text: #dbe7ff;
        --image-bg: #1f2b44;
      }
      body {
        font-family: Inter, Arial, sans-serif;
        margin: 0;
        background: var(--bg-gradient);
        color: var(--text);
      }
      .theme-toggle {
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 20;
      }
      .container {
        max-width: 900px;
        margin: 2rem auto;
        padding: 0 1rem 2rem;
      }
      .card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 18px;
        padding: 1.25rem;
        box-shadow: 0 12px 28px rgba(38, 77, 182, 0.12);
      }
      h1, h2 { margin: 0 0 0.75rem; }
      .search-row {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
      }
      .search-row > * {
        flex: 1 1 220px;
      }
      input, button {
        border-radius: 12px;
        border: 1px solid var(--input-border);
        padding: 0.7rem 0.9rem;
        font-size: 1rem;
      }
      input {
        background: var(--item-bg);
        color: var(--text);
      }
      input { min-width: 0; }
      button {
        background: #2f63ff;
        color: white;
        cursor: pointer;
        font-weight: 600;
      }
      .muted { color: var(--muted); font-size: 0.95rem; }
      #status { margin-top: 0.85rem; font-weight: 600; }
      ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.8rem; }
      li {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        background: var(--item-bg);
        border: 1px solid var(--item-border);
        border-radius: 12px;
        padding: 0.6rem 0.8rem;
      }
      img {
        width: 58px;
        height: 58px;
        border-radius: 10px;
        object-fit: cover;
        background: var(--image-bg);
      }
      .badge {
        margin-left: auto;
        background: var(--badge-bg);
        color: var(--badge-text);
        border-radius: 999px;
        padding: 0.25rem 0.55rem;
        font-size: 0.85rem;
      }
      @media (max-width: 640px) {
        .container {
          margin: 1rem auto;
          padding: 0 0.75rem 1rem;
        }
        .card {
          border-radius: 14px;
          padding: 1rem;
        }
        .search-row {
          flex-direction: column;
        }
        .search-row > * {
          width: 100%;
          flex-basis: auto;
        }
        button {
          min-height: 44px;
        }
        li {
          align-items: flex-start;
          flex-wrap: wrap;
        }
        .badge {
          margin-left: 0;
        }
      }
      .shopping-list-section { margin-top: 1rem; }
      .danger-button {
        margin-top: 0.85rem;
        width: 100%;
        background: #cf202f;
        border-color: #b81b29;
      }
      .danger-button:hover { background: #b81b29; }
      .variant-section { margin-top: 1rem; }
      .variant-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 0.75rem;
      }
      .variant-card {
        background: var(--item-bg);
        border: 1px solid var(--item-border);
        border-radius: 12px;
        padding: 0.6rem;
        text-align: center;
      }
      .variant-card button {
        width: 100%;
        background: transparent;
        border: none;
        padding: 0;
        color: inherit;
      }
      .variant-card img {
        width: 72px;
        height: 72px;
        margin-bottom: 0.4rem;
        cursor: pointer;
      }
    </style>
  </head>
  <body>
    <button id='theme-toggle' class='theme-toggle' onclick='toggleTheme()'>🌙 Darkmode</button>
    <main class='container'>
      <section class='card'>
        <h1>Grocy AI Suche</h1>
        <p class='muted'>Produkt eingeben: vorhanden → Einkaufsliste, nicht vorhanden → per KI anlegen + Einkaufsliste.</p>
        <div class='search-row'>
          <input id='name' placeholder='z.B. Hafermilch 1L' />
          <button onclick='searchProduct()'>Suchen & hinzufügen</button>
          <button onclick='loadShoppingList()'>Einkaufsliste aktualisieren</button>
        </div>
        <p id='status'>Bereit.</p>
      </section>

      <section class='card variant-section'>
        <h2>Gefundene Produktvarianten</h2>
        <p class='muted'>Teilnamen wie "apf" zeigen passende Produkte. Klick auf das Bild fügt den Artikel direkt zur Einkaufsliste hinzu.</p>
        <div id='variant-list' class='variant-grid'></div>
      </section>

      <section class='card shopping-list-section'>
        <h2>Einkaufsliste</h2>
        <p class='muted'>Direkt aus Grocy geladen, inklusive Produktbildern (falls vorhanden).</p>
        <ul id='shopping-list'></ul>
        <button class='danger-button' onclick='clearShoppingList()'>Einkaufsliste leeren</button>
      </section>
    </main>

    <script>
      const configuredApiKey = __CONFIGURED_API_KEY__;
      const apiBasePath = __API_BASE_PATH__;
      const themeStorageKey = 'grocy-dashboard-theme';
      let apiKey = configuredApiKey || '';
      const ingressPrefixMatch = window.location.pathname.match(/^\/api\/hassio_ingress\/[^\/]+/);
      const ingressPrefix = ingressPrefixMatch ? ingressPrefixMatch[0] : '';

      function applyTheme(theme) {
        const root = document.documentElement;
        const toggle = document.getElementById('theme-toggle');

        if (theme === 'dark') {
          root.setAttribute('data-theme', 'dark');
          toggle.textContent = '☀️ Lightmode';
          return;
        }

        root.removeAttribute('data-theme');
        toggle.textContent = '🌙 Darkmode';
      }

      function toggleTheme() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const nextTheme = isDark ? 'light' : 'dark';
        localStorage.setItem(themeStorageKey, nextTheme);
        applyTheme(nextTheme);
      }

      function ensureApiKey() {
        return apiKey;
      }

      async function parseJsonSafe(response) {
        try {
          return await response.json();
        } catch (_) {
          return {};
        }
      }

      function buildApiUrl(path) {
        const normalizedPath = '/' + String(path || '').replace(/^\/+/, '');
        if (apiBasePath) {
          return `${apiBasePath}${normalizedPath}`;
        }
        if (ingressPrefix) {
          return `${ingressPrefix}${normalizedPath}`;
        }
        return normalizedPath.replace(/^\//, '');
      }

      function toImageSource(url) {
        if (!url) return 'https://placehold.co/80x80?text=Kein+Bild';
        if (url.startsWith('data:')) return url;
        if (url.startsWith('http://') || url.startsWith('https://')) {
          const isExternal = (() => {
            try {
              return new URL(url).host !== window.location.host;
            } catch (_) {
              return false;
            }
          })();

          if (window.location.protocol === 'https:' && isExternal && url.startsWith('http://')) {
            return 'https://' + url.slice('http://'.length);
          }
          return url;
        }
        const normalized = '/' + url.replace(/^\/+/, '');
        if (normalized.startsWith('/api/')) {
          return buildApiUrl(normalized);
        }
        return normalized;
      }

      function renderShoppingList(items) {
        const list = document.getElementById('shopping-list');
        if (!items.length) {
          list.innerHTML = '<li>Keine Einträge in der Einkaufsliste.</li>';
          return;
        }

        list.innerHTML = items.map((item) => `
          <li>
            <img src="${toImageSource(item.picture_url)}" alt="${item.product_name}" loading="lazy" />
            <div>
              <div><strong>${item.product_name}</strong></div>
              <div class="muted">${item.note || 'Keine Notiz'}</div>
            </div>
            <span class="badge">Menge: ${item.amount}</span>
          </li>
        `).join('');
      }

      async function loadShoppingList() {
        const key = ensureApiKey();
        const status = document.getElementById('status');
        if (!key) {
          status.textContent = 'Kein API-Key angegeben.';
          return;
        }

        status.textContent = 'Lade Einkaufsliste...';
        try {
          const res = await fetch(buildApiUrl('/api/dashboard/shopping-list'), {
            headers: { 'Authorization': `Bearer ${key}` },
          });
          const payload = await parseJsonSafe(res);

          if (!res.ok) {
            status.textContent = payload.detail || 'Einkaufsliste konnte nicht geladen werden.';
            return;
          }

          renderShoppingList(payload);
          status.textContent = `Einkaufsliste geladen (${payload.length} Einträge).`;
        } catch (_) {
          status.textContent = 'Einkaufsliste konnte nicht geladen werden (Netzwerk-/Ingress-Fehler).';
        }
      }

      function renderVariants(items) {
        const list = document.getElementById('variant-list');
        if (!items.length) {
          list.innerHTML = '<div class="muted">Keine passenden Varianten gefunden.</div>';
          return;
        }

        list.innerHTML = items.map((item) => `
          <div class="variant-card">
            <button type="button" class="variant-select" data-product-id="${item.id}" data-product-name="${encodeURIComponent(item.name)}">
              <img src="${toImageSource(item.picture_url)}" alt="${item.name}" loading="lazy" />
              <div><strong>${item.name}</strong></div>
            </button>
          </div>
        `).join('');
      }

      async function loadVariants() {
        const key = ensureApiKey();
        const status = document.getElementById('status');
        const name = document.getElementById('name').value || '';

        if (!key) return;

        const query = name.trim();
        if (!query) {
          document.getElementById('variant-list').innerHTML = '';
          return;
        }

        try {
          const res = await fetch(buildApiUrl(`/api/dashboard/search-variants?q=${encodeURIComponent(query)}`), {
            headers: { 'Authorization': `Bearer ${key}` },
          });
          const payload = await parseJsonSafe(res);

          if (!res.ok) {
            status.textContent = payload.detail || 'Varianten konnten nicht geladen werden.';
            return;
          }

          renderVariants(payload);
        } catch (_) {
          status.textContent = 'Varianten konnten nicht geladen werden (Netzwerk-/Ingress-Fehler).';
        }
      }

      async function confirmVariant(productId, productName) {
        const key = ensureApiKey();
        const status = document.getElementById('status');

        if (!key) {
          status.textContent = 'Kein API-Key angegeben.';
          return;
        }

        status.textContent = `Füge ${productName} zur Einkaufsliste hinzu...`;
        try {
          const res = await fetch(buildApiUrl('/api/dashboard/add-existing-product'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
            body: JSON.stringify({ product_id: productId, product_name: productName }),
          });
          const payload = await parseJsonSafe(res);
          status.textContent = payload.message || payload.detail || 'Unbekannte Antwort';

          if (res.ok) {
            await loadShoppingList();
          }
        } catch (_) {
          status.textContent = 'Produkt konnte nicht hinzugefügt werden (Netzwerk-/Ingress-Fehler).';
        }
      }

      async function clearShoppingList() {
        const key = ensureApiKey();
        const status = document.getElementById('status');
        if (!key) {
          status.textContent = 'Kein API-Key angegeben.';
          return;
        }

        status.textContent = 'Leere Einkaufsliste...';
        try {
          const res = await fetch(buildApiUrl('/api/dashboard/shopping-list/clear'), {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${key}` },
          });
          const payload = await parseJsonSafe(res);

          if (!res.ok) {
            status.textContent = payload.detail || 'Einkaufsliste konnte nicht geleert werden.';
            return;
          }

          status.textContent = payload.message || 'Einkaufsliste geleert.';
          await loadShoppingList();
        } catch (_) {
          status.textContent = 'Einkaufsliste konnte nicht geleert werden (Netzwerk-/Ingress-Fehler).';
        }
      }

      async function searchProduct() {
        const name = document.getElementById('name').value;
        const status = document.getElementById('status');
        const key = ensureApiKey();

        if (!key) {
          status.textContent = 'Kein API-Key angegeben.';
          return;
        }
        if (!name || !name.trim()) {
          status.textContent = 'Bitte Produktname eingeben.';
          return;
        }

        status.textContent = 'Prüfe Produkt...';
        try {
          const res = await fetch(buildApiUrl('/api/dashboard/search'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
            body: JSON.stringify({ name })
          });

          const payload = await parseJsonSafe(res);
          status.textContent = payload.message || payload.detail || 'Unbekannte Antwort';

          if (res.ok) {
            await loadShoppingList();
          }
        } catch (_) {
          status.textContent = 'Produkt konnte nicht geprüft werden (Netzwerk-/Ingress-Fehler).';
        }
      }

      let variantsDebounce;
      document.getElementById('variant-list').addEventListener('click', (event) => {
        const target = event.target.closest('.variant-select');
        if (!target) return;

        const productId = Number(target.dataset.productId);
        const productName = decodeURIComponent(target.dataset.productName || '');
        confirmVariant(productId, productName);
      });

      document.getElementById('name').addEventListener('input', () => {
        clearTimeout(variantsDebounce);
        variantsDebounce = setTimeout(() => {
          loadVariants();
        }, 250);
      });

      const savedTheme = localStorage.getItem(themeStorageKey) || 'light';
      applyTheme(savedTheme);
      loadShoppingList();
      loadVariants();
    </script>
  </body>
</html>
""".replace(
        "__CONFIGURED_API_KEY__", configured_api_key
    ).replace(
        "__API_BASE_PATH__", api_base_path
    )


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, settings: Settings = Depends(get_settings)) -> str:
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
