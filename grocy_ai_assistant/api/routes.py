import json
import logging
from urllib.parse import urljoin

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse

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
                picture_url=_build_product_picture_url(
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


@router.get("/", response_class=HTMLResponse)
def dashboard(settings: Settings = Depends(get_settings)) -> str:
    configured_api_key = json.dumps(settings.api_key)
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
      let apiKey = configuredApiKey || '';

      function ensureApiKey() {
        return apiKey;
      }

      function toImageSource(url) {
        if (!url) return 'https://placehold.co/80x80?text=Kein+Bild';
        if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) return url;
        return '/' + url.replace(/^\/+/, '');
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
        const res = await fetch('/api/dashboard/shopping-list', {
          headers: { 'Authorization': `Bearer ${key}` },
        });
        const payload = await res.json();

        if (!res.ok) {
          status.textContent = payload.detail || 'Einkaufsliste konnte nicht geladen werden.';
          return;
        }

        renderShoppingList(payload);
        status.textContent = `Einkaufsliste geladen (${payload.length} Einträge).`;
      }

      async function clearShoppingList() {
        const key = ensureApiKey();
        const status = document.getElementById('status');
        if (!key) {
          status.textContent = 'Kein API-Key angegeben.';
          return;
        }

        status.textContent = 'Leere Einkaufsliste...';
        const res = await fetch('/api/dashboard/shopping-list/clear', {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${key}` },
        });
        const payload = await res.json();

        if (!res.ok) {
          status.textContent = payload.detail || 'Einkaufsliste konnte nicht geleert werden.';
          return;
        }

        status.textContent = payload.message || 'Einkaufsliste geleert.';
        await loadShoppingList();
      }

      async function searchProduct() {
        const name = document.getElementById('name').value;
        const status = document.getElementById('status');
        const key = ensureApiKey();

        if (!key) {
          status.textContent = 'Kein API-Key angegeben.';
          return;
        }

        status.textContent = 'Prüfe Produkt...';
        const res = await fetch('/api/dashboard/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
          body: JSON.stringify({ name })
        });

        const payload = await res.json();
        status.textContent = payload.message || payload.detail || 'Unbekannte Antwort';

        if (res.ok) {
          await loadShoppingList();
        }
      }

      loadShoppingList();
    </script>
  </body>
</html>
""".replace(
        "__CONFIGURED_API_KEY__", configured_api_key
    )
