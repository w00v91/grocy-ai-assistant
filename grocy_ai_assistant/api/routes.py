import json
import logging
from urllib.parse import quote, urljoin, urlparse

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from grocy_ai_assistant.ai.ingredient_detector import IngredientDetector
from grocy_ai_assistant.config.settings import Settings, get_settings
from grocy_ai_assistant.models.ingredient import (
    AnalyzeProductRequest,
    AnalyzeProductResponse,
    DashboardSearchResponse,
    ShoppingListItemResponse,
)
from grocy_ai_assistant.services.grocy_client import GrocyClient

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_product_picture_url(raw_picture_url: str, settings: Settings) -> str:
    picture_value = (raw_picture_url or "").strip()
    if not picture_value:
        return ""

    if picture_value.startswith(("http://", "https://", "data:")):
        return picture_value

    grocy_base_url = settings.grocy_base_url.rstrip("/")

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


def require_auth(
    authorization: str = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if authorization != f"Bearer {settings.api_key}":
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

    response = requests.get(
        src,
        headers={"GROCY-API-KEY": settings.grocy_api_key},
        timeout=30,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden") from error

    content_type = response.headers.get("Content-Type", "image/jpeg")
    return Response(content=response.content, media_type=content_type)


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
                    item.get("picture_url")
                    or item.get("product_picture_url")
                    or item.get("picture_file_name")
                    or "",
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
    return """
<!doctype html>
<html lang='de'>
  <head>
    <meta charset='utf-8' />
    <meta name='viewport' content='width=device-width,initial-scale=1' />
    <title>Grocy AI Dashboard</title>
    <style>
      :root {
        color-scheme: light dark;
      }
      body {
        font-family: Inter, Arial, sans-serif;
        margin: 0;
        background: linear-gradient(140deg, #f3f6ff 0%, #f6fbf8 55%, #ecf4ff 100%);
        color: #1f2937;
      }
      .container {
        max-width: 900px;
        margin: 2rem auto;
        padding: 0 1rem 2rem;
      }
      .card {
        background: rgba(255, 255, 255, 0.86);
        border: 1px solid #dbe6ff;
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
        border: 1px solid #cad6f8;
        padding: 0.7rem 0.9rem;
        font-size: 1rem;
      }
      input { min-width: 0; }
      button {
        background: #2f63ff;
        color: white;
        cursor: pointer;
        font-weight: 600;
      }
      .muted { color: #5f6d85; font-size: 0.95rem; }
      #status { margin-top: 0.85rem; font-weight: 600; }
      ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.8rem; }
      li {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        background: #fff;
        border: 1px solid #e6ecff;
        border-radius: 12px;
        padding: 0.6rem 0.8rem;
      }
      img {
        width: 58px;
        height: 58px;
        border-radius: 10px;
        object-fit: cover;
        background: #eef2f9;
      }
      .badge {
        margin-left: auto;
        background: #edf2ff;
        color: #3555ad;
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
    </style>
  </head>
  <body>
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
      let apiKey = configuredApiKey || '';
      const ingressPrefixMatch = window.location.pathname.match(/^\/api\/hassio_ingress\/[^\/]+/);
      const ingressPrefix = ingressPrefixMatch ? ingressPrefixMatch[0] : '';

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
        const normalized = '/' + url.replace(/^\\/+/, '');
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

      loadShoppingList();
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
