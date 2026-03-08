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

@app.route('/api/status', methods=['GET'])
def get_status():
    """Status-Check für den HA-Sensor."""
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {EXPECTED_API_KEY}":
        logger.warning("Unbefugter Status-Abrufversuch.")
        return jsonify({"status": "Nicht autorisiert"}), 401
    
    return jsonify({
        "status": "Verbunden",
        "ollama_target": OLLAMA_URL,
        "model": options.get("ollama_model", "llama3")
    })

@app.route('/api/process', methods=['POST'])
def process_data():
    """Verarbeitet KI-Anfragen und leitet sie an Ollama weiter."""
    # 1. Auth-Check
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {EXPECTED_API_KEY}":
        return jsonify({"error": "Unauthorized"}), 401

    # 2. Daten extrahieren
    data = request.json
    prompt = data.get("prompt", "")

    # 3. Payload für Ollama vorbereiten
    ollama_payload = {
        "model": options.get("ollama_model", "llama3"),
        "prompt": prompt,
        "stream": False
    }

    try:
        # Anfrage an Ollama senden
        response = requests.post(OLLAMA_URL, json=ollama_payload, timeout=60)
        response.raise_for_status()
        ollama_data = response.json()
        
        return jsonify({
            "answer": ollama_data.get("response"),
            "success": True
        })
    except Exception as e:
        logger.error(f"Ollama-Fehler: {e}")
        return jsonify({"error": str(e), "success": False}), 500

if __name__ == '__main__':
    # 'flush=True' ist der wichtigste Teil hier!
    print(">>> FLASK SERVICE STARTET JETZT AUF PORT 8000 <<<", flush=True)
    logger.info("Service ist bereit für Anfragen.")
    app.run(host='0.0.0.0', port=8000, debug=False)