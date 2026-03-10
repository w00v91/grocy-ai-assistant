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
pip install -r grocy_ai_assistant/requirements.txt
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


## Architektur-Notizen

- **API-Schicht (`api/`)** bleibt rein für HTTP-Endpunkte, Dashboard-Rendering und Request-Validierung.
- **Domain/Orchestrierung (`core/`)** enthält die Ablaufsteuerung für Analyse und Produktlogik.
- **Service-Schicht (`services/`)** kapselt die Grocy-Kommunikation vollständig.
- **Integration (`custom_components/`)** ruft das Add-on über den `AddonClient` auf und enthält keine direkte Grocy- oder Ollama-HTTP-Logik mehr.

### Ingress & Dashboard

- Das Dashboard baut API-URLs robust für Standardbetrieb und Home-Assistant-Ingress (`/api/hassio_ingress/...`).
- Panel-URLs werden normalisiert: absolute Ingress-URLs werden auf den relativen Ingress-Pfad reduziert, Loopback-Ziele (`localhost`, `127.0.0.1`, `::1`) automatisch auf den Standard-Ingress-Fallback gesetzt.
- Produktbilder werden über einen Proxy-Endpunkt bereitgestellt, damit Authentifizierung und gemischte HTTP/HTTPS-Szenarien stabil bleiben.

## Versionen

Aktueller Stand:
- **Add-on:** `6.0.2`
- **Integration:** `2.0.2`

## Qualitätssicherung

```bash
pytest
ruff check .
black .
```

### Testumfang (Kurzüberblick)

- API-Tests für Status, Dashboard, HTTPS-Redirect und Produkt-Workflow
- Unit-Tests für Engine, Grocy-Client, Add-on-Client und Panel-URL-Logik
- Hilfsfunktions-Tests für Produktbild-URL-Aufbereitung


## Architektur-Review (aktueller Stand)

Positiv aufgefallen:
- Saubere Schichtentrennung zwischen API (`api/`), Orchestrierung (`core/`), KI (`ai/`) und Grocy-Client (`services/`).
- Gute Testabdeckung für API-Flows, Ingress-/Panel-Logik und Service-Clients.

Verbesserungen in diesem Update:
- FastAPI-Lifecycle auf modernes `lifespan`-Pattern umgestellt (statt veraltetem `on_event`).
- App-Erzeugung über `create_app()` gekapselt, damit Initialisierung klarer und langfristig testfreundlicher ist.
- Versionierung auf neuen Major-Stand angehoben (Add-on + Integration synchron).

Empfohlene nächste Schritte (optional):
- Das große Inline-Dashboard-HTML langfristig in Templates/Static-Dateien auslagern, um Wartbarkeit weiter zu steigern.
- API-Auth mittelfristig auf zentrale Security-Dependency (z. B. `HTTPBearer`) umstellen.

