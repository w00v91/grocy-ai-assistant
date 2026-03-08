import json
import os
import logging
from flask import Flask, request, jsonify

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GrocyAIAssistant")

app = Flask(__name__)

def get_addon_options():
    """Liest die Konfiguration aus dem Home Assistant Add-on System."""
    options_path = "/data/options.json"
    if os.path.exists(options_path):
        with open(options_path, 'r') as f:
            return json.load(f)
    logger.warning("Keine options.json gefunden, nutze Standardwerte.")
    return {}

# Optionen laden
options = get_addon_options()
GROCY_API_KEY = options.get("grocy_api_key", "")
ENABLE_OPTIMIZER = options.get("enable_optimizer", True)

@app.route("/process", methods=["POST"])
def process_request():
    """Beispiel-Endpoint für die Custom Integration."""
    data = request.json
    user_input = data.get("text", "")
    
    logger.info(f"KI verarbeitet Anfrage: {user_input}")
    
    # HIER KOMMT DEINE KI-LOGIK REIN (z.B. OpenAI Call oder lokales Modell)
    # Beispiel-Antwort:
    response = {
        "status": "ok",
        "answer": f"Ich habe '{user_input}' für Grocy verarbeitet.",
        "action_taken": "inventory_sync"
    }
    
    return jsonify(response)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "grocy_connected": bool(GROCY_API_KEY)})

if __name__ == "__main__":
    # Home Assistant Add-ons nutzen oft Port 8000 oder den in config.json definierten
    logger.info("Grocy AI Assistant Service startet auf Port 8000...")
    app.run(host="0.0.0.0", port=8000)