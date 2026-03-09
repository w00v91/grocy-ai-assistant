import requests
import json
import sys
import logging
import os
from flask import Flask, request, jsonify

# 1. Logging radikal erzwingen
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # Erzwingt die Ausgabe in den Docker-Standard-Stream
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Deaktiviere den Flask-internen Puffer
app.config['ENV'] = 'development' 

@app.before_request
def log_request_info():
    # Diese Funktion schreibt JEDE Anfrage sofort ins Log
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

# Konfiguration initial laden
options = get_addon_options()
# Falls kein Key gesetzt ist, wird ein Fallback genutzt
EXPECTED_API_KEY = options.get("api_key", "standard_passwort")
OLLAMA_URL = options.get("ollama_url", "http://localhost:11434/api/generate")

# --- HILFSFUNKTION FÜR GROCY KONTEXT ---
def get_grocy_context():
    """
    Hier könnten wir später die echten IDs von Grocy abrufen.
    Vorerst nutzen wir Standardwerte, damit die KI weiß, was sie tun soll.
    """
    return {
        "locations": "1: Kuehlschrank, 2: Vorratsschrank, 3: Tiefkuehler",
        "units": "1: Stueck, 2: Packung, 3: Gramm, 4: Kilogramm"
    }

@app.route('/api/status', methods=['GET'])
def get_status():
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {EXPECTED_API_KEY}":
        return jsonify({"status": "Nicht autorisiert"}), 401
    return jsonify({"status": "Verbunden", "ollama_ready": True})

# Ein Prompt-Template für die Bildgenerierung
IMAGE_PROMPT_TEMPLATE = """
Professionelles Produktfoto von '{product_name}' auf rein weißem Hintergrund. 
Studiobeleuchtung, scharf, keine Wasserzeichen, fotorealistisch.
"""

def generate_product_image(product_name):
    """Erstellt ein Produktbild via Stable Diffusion/Ollama."""
    prompt = IMAGE_PROMPT_TEMPLATE.format(product_name=product_name)
    
    # URL deines Stable Diffusion Endpunkts (z.B. lokal oder in der Cloud)
    SD_URL = "http://172.17.0.1:7860/sdapi/v1/txt2img" 
    
    # Payload für die Generierung
    payload = {
        "prompt": prompt,
        "steps": 20,
        "width": 512,
        "height": 512,
        "cfg_scale": 7
    }

    try:
        response = requests.post(SD_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        # Stable Diffusion gibt oft ein Base64 Bild zurück
        r = response.json()
        image_base64 = r['images'][0]
        
        # Als Datei zwischenspeichern
        file_path = f"/data/product_images/{product_name.replace(' ', '_')}.png"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(image_base64))
            
        return file_path # Rückgabe des lokalen Pfads
    except Exception as e:
        logger.error(f"Bildgenerierung fehlgeschlagen: {e}")
    return None

@app.route('/api/analyze_product', methods=['POST'])
def analyze():
    app.logger.info("ANALYSE-ANFRAGE GEKOMMEN!")
    """Analysiert ein Produkt und liefert strukturiertes JSON für Grocy."""
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {EXPECTED_API_KEY}":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    product_name = data.get("name", "")
    context = get_grocy_context()

    # Der System-Prompt zwingt die KI in ein festes JSON-Format
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
        "format": "json" # Wichtig: Erzwingt JSON-Ausgabe bei modernen Modellen
    }

    try:
        response = requests.post(OLLAMA_URL, json=ollama_payload, timeout=60)
        response.raise_for_status()
        raw_answer = response.json().get("response")
        
        # Die Antwort der KI direkt als JSON parsen und zurueckgeben
        return jsonify({
            "product_data": json.loads(raw_answer),
            "success": True
        })
    except Exception as e:
        logger.error(f"Analyse-Fehler: {e}")
        return jsonify({"error": str(e), "success": False}), 500

if __name__ == '__main__':
    print(">>> GROCY AI ENGINE GESTARTET AUF PORT 8000 <<<", flush=True)
    app.run(host='0.0.0.0', port=8000, debug=False)