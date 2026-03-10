# Grocy AI Assistant

KI-gestütztes Add-on für Home Assistant, das Produkte erkennt, bei Bedarf in Grocy anlegt und direkt zur Einkaufsliste hinzufügt.

## Überblick

Das Projekt besteht aus zwei eng gekoppelten Teilen:
- **Home Assistant Add-on (FastAPI-Service)** für Analyse- und Dashboard-Endpunkte.
- **Home Assistant Custom Integration** für Statussensor und Kommunikation mit dem Add-on.

Damit beide Teile kompatibel bleiben, werden Add-on- und Integrationsversion gemeinsam gepflegt.

## Features

- FastAPI API für Produktanalyse und Dashboard-Workflows
- KI-Produktklassifizierung über Ollama
- Automatische Grocy-Produktanlage inkl. Einkaufsliste-Workflow
- Home-Assistant-Sensor mit Versions-/Restart-Hinweis
- Leichtgewichtiges Dashboard unter `/`

## Projektstruktur

```text
grocy_ai_assistant/
├── api/                                # FastAPI App + Routen
├── ai/                                 # KI-Logik (IngredientDetector)
├── config/                             # Laufzeit-Settings
├── core/                               # Orchestrierung / Engine
├── custom_components/grocy_ai_assistant/  # Home Assistant Integration
├── db/                                 # Persistente Daten (z. B. Mappings)
├── models/                             # Pydantic Modelle
└── services/                           # Grocy API Client
```

## Voraussetzungen

- Python 3.11+
- Laufender Grocy-Server
- Optional: Ollama-Server (für KI-gestützte Produktdaten)

## Lokale Entwicklung

```bash
pip install -r requirements.txt
python -m grocy_ai_assistant.api.main
```

API läuft anschließend standardmäßig auf `http://localhost:8000`.

## Wichtige Endpunkte

- `GET /api/status` – Verbindung, Versionen, Restart-Hinweis
- `POST /api/analyze_product` – analysiert Produktnamen
- `POST /api/dashboard/search` – findet/erstellt Produkt und fügt zur Einkaufsliste hinzu
- `GET /api/dashboard/shopping-list` – holt aktuelle Einkaufsliste
- `GET /` – integriertes Dashboard

## Konfiguration

Primär über Add-on Optionen (`/data/options.json`) bzw. Umgebungsvariablen.

Wichtige Felder:
- `api_key`
- `grocy_api_key`
- `grocy_base_url`
- `ollama_url`
- `ollama_model`
- `required_integration_version`

## Versionen

Aktueller Stand:
- **Add-on:** `5.2.19`
- **Integration:** `1.2.15`

## Qualitätssicherung

```bash
pytest
ruff check .
black .
```
