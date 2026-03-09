import base64
import json
import logging
import os
import sys

import requests
from flask import Flask, jsonify, request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['ENV'] = 'development'


@app.before_request
def log_request_info():
    logger.info(f"Anfrage erhalten: {request.method} {request.path}")


def get_addon_options():
    """Liest die Add-on Konfiguration aus der Datei des Supervisors."""
    options_path = '/data/options.json'
    if os.path.exists(options_path):
        try:
            with open(options_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Fehler beim Lesen der options.json: {e}")
    return {}


options = get_addon_options()
EXPECTED_API_KEY = options.get("api_key", "standard_passwort")
OLLAMA_URL = options.get("ollama_url", "http://10.0.0.2:11434/api/generate")
GROCY_BASE_URL = options.get("grocy_base_url", "http://homeassistant.local:9192/api")
GROCY_API_KEY = options.get("grocy_api_key", "")


def _normalize_name(value: str) -> str:
    return (value or "").strip().casefold()


def _auth_ok() -> bool:
    auth_header = request.headers.get("Authorization")
    return auth_header == f"Bearer {EXPECTED_API_KEY}"


def _grocy_headers():
    return {
        "GROCY-API-KEY": GROCY_API_KEY,
        "Content-Type": "application/json",
    }


def get_grocy_context():
    return {
        "locations": "1: Kuehlschrank, 2: Vorratsschrank, 3: Tiefkuehler",
        "units": "1: Stueck, 2: Packung, 3: Gramm, 4: Kilogramm",
    }


def analyze_product_name(product_name: str):
    context = get_grocy_context()
    prompt = f"""
    Analysiere das Produkt '{product_name}'.
    Gib NUR ein JSON-Objekt zurueck, das exakt diese Struktur hat:
    {{
      "name": "{product_name}",
      "description": "kurze Beschreibung",
      "location_id": (Waehle aus: {context['locations']}),
      "qu_id_purchase": (Waehle aus: {context['units']}),
      "qu_id_stock": (Waehle aus: {context['units']}),
      "calories": (Geschaetzte Kalorien pro 100g/ml als Zahl)
    }}
    Antworte NUR mit dem JSON, kein Text davor oder danach.
    """

    ollama_payload = {
        "model": options.get("ollama_model", "llama3"),
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    response = requests.post(OLLAMA_URL, json=ollama_payload, timeout=60)
    response.raise_for_status()
    raw_answer = response.json().get("response")
    return json.loads(raw_answer)


@app.route('/api/status', methods=['GET'])
def get_status():
    if not _auth_ok():
        return jsonify({"status": "Nicht autorisiert"}), 401
    return jsonify({"status": "Verbunden", "ollama_ready": True})


IMAGE_PROMPT_TEMPLATE = """
Professionelles Produktfoto von '{product_name}' auf rein weißem Hintergrund.
Studiobeleuchtung, scharf, keine Wasserzeichen, fotorealistisch.
"""


def generate_product_image(product_name):
    prompt = IMAGE_PROMPT_TEMPLATE.format(product_name=product_name)
    sd_url = "http://172.17.0.1:7860/sdapi/v1/txt2img"
    payload = {
        "prompt": prompt,
        "steps": 20,
        "width": 512,
        "height": 512,
        "cfg_scale": 7,
    }

    try:
        response = requests.post(sd_url, json=payload, timeout=60)
        response.raise_for_status()
        image_base64 = response.json()['images'][0]
        file_path = f"/data/product_images/{product_name.replace(' ', '_')}.png"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(image_base64))
        return file_path
    except Exception as e:
        logger.error(f"Bildgenerierung fehlgeschlagen: {e}")
    return None


@app.route('/api/analyze_product', methods=['POST'])
def analyze():
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    product_name = data.get("name", "")
    if not product_name:
        return jsonify({"error": "Produktname fehlt", "success": False}), 400

    try:
        return jsonify({"product_data": analyze_product_name(product_name), "success": True})
    except Exception as e:
        logger.error(f"Analyse-Fehler: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/api/dashboard/search', methods=['POST'])
def dashboard_search():
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401

    if not GROCY_API_KEY:
        return jsonify({"error": "grocy_api_key fehlt in Add-on Optionen"}), 500

    data = request.json or {}
    product_name = data.get("name", "").strip()
    if not product_name:
        return jsonify({"error": "Bitte Produktname eingeben"}), 400

    headers = _grocy_headers()
    try:
        products_resp = requests.get(f"{GROCY_BASE_URL}/objects/products", headers=headers, timeout=30)
        products_resp.raise_for_status()
        products = products_resp.json()

        existing_product = next(
            (p for p in products if _normalize_name(p.get("name")) == _normalize_name(product_name)),
            None,
        )

        if existing_product:
            add_resp = requests.post(
                f"{GROCY_BASE_URL}/stock/shoppinglist/add-product",
                headers=headers,
                json={"product_id": existing_product.get("id"), "amount": 1},
                timeout=30,
            )
            add_resp.raise_for_status()
            return jsonify({
                "success": True,
                "action": "existing_added",
                "message": f"{product_name} war vorhanden und wurde zur Einkaufsliste hinzugefügt.",
            })

        product_data = analyze_product_name(product_name)
        create_resp = requests.post(
            f"{GROCY_BASE_URL}/objects/products",
            headers=headers,
            json=product_data,
            timeout=30,
        )
        create_resp.raise_for_status()
        created_object_id = create_resp.json().get("created_object_id")

        add_resp = requests.post(
            f"{GROCY_BASE_URL}/stock/shoppinglist/add-product",
            headers=headers,
            json={"product_id": created_object_id, "amount": 1},
            timeout=30,
        )
        add_resp.raise_for_status()

        return jsonify({
            "success": True,
            "action": "created_and_added",
            "message": f"{product_name} wurde neu angelegt und zur Einkaufsliste hinzugefügt.",
            "product_id": created_object_id,
        })
    except Exception as e:
        logger.error(f"Dashboard-Workflow Fehler: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/', methods=['GET'])
def dashboard():
    return """
<!doctype html>
<html lang='de'>
  <head>
    <meta charset='utf-8' />
    <meta name='viewport' content='width=device-width,initial-scale=1' />
    <title>Grocy AI Dashboard</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; background: #111827; color: #e5e7eb; }
      .wrap { max-width: 760px; margin: 2rem auto; padding: 1rem; }
      .card { background: #1f2937; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
      input, button { font-size: 1rem; padding: 0.6rem; border-radius: 8px; border: none; }
      input { width: calc(100% - 140px); margin-right: 8px; }
      button { width: 120px; background: #2563eb; color: white; cursor: pointer; }
      .muted { color: #9ca3af; }
    </style>
  </head>
  <body>
    <div class='wrap'>
      <div class='card'>
        <h2>Grocy AI Suche</h2>
        <p class='muted'>Produkt eingeben: vorhanden → Einkaufsliste, nicht vorhanden → per KI anlegen + Einkaufsliste.</p>
        <input id='name' placeholder='z.B. Hafermilch 1L' />
        <button onclick='searchProduct()'>Suchen</button>
        <p id='status' class='muted'>Bereit.</p>
      </div>

      <div class='card'>
        <h3>Weitere Funktionen (Roadmap)</h3>
        <ul>
          <li>Ähnliche Produkte vorschlagen</li>
          <li>Mehrere Produkte als Batch hinzufügen</li>
          <li>Einkaufsvorschläge nach Rezepten</li>
        </ul>
      </div>
    </div>

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
        status.textContent = payload.message || payload.error || 'Unbekannte Antwort';
      }
    </script>
  </body>
</html>
"""


if __name__ == '__main__':
    print(">>> GROCY AI ENGINE GESTARTET AUF PORT 8000 <<<", flush=True)
    app.run(host='0.0.0.0', port=8000, debug=False)
