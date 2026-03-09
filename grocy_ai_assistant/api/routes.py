import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse

from grocy_ai_assistant.ai.ingredient_detector import IngredientDetector
from grocy_ai_assistant.config.settings import Settings, get_settings
from grocy_ai_assistant.models.ingredient import (
    AnalyzeProductRequest,
    AnalyzeProductResponse,
    DashboardSearchResponse,
)
from grocy_ai_assistant.services.grocy_client import GrocyClient

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return """
<!doctype html>
<html lang='de'>
  <head>
    <meta charset='utf-8' />
    <meta name='viewport' content='width=device-width,initial-scale=1' />
    <title>Grocy AI Dashboard</title>
  </head>
  <body style="font-family: Arial, sans-serif; margin: 2rem;">
    <h2>Grocy AI Suche</h2>
    <p>Produkt eingeben: vorhanden → Einkaufsliste, nicht vorhanden → per KI anlegen + Einkaufsliste.</p>
    <input id='name' placeholder='z.B. Hafermilch 1L' />
    <button onclick='searchProduct()'>Suchen</button>
    <p id='status'>Bereit.</p>
    <script>
      async function searchProduct() {
        const name = document.getElementById('name').value;
        const status = document.getElementById('status');
        status.textContent = 'Prüfe Produkt...';
        const apiKey = prompt('Bitte API-Key eingeben:');
        if (!apiKey) {
          status.textContent = 'Kein API-Key angegeben.';
          return;
        }

        const res = await fetch('/api/dashboard/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
          body: JSON.stringify({ name })
        });

        const payload = await res.json();
        status.textContent = payload.message || payload.detail || 'Unbekannte Antwort';
      }
    </script>
  </body>
</html>
"""
