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
- **Shared-Utilities (`core/picture_urls.py`)** bündeln die Normalisierung von Produktbild-URLs, damit API und Bild-Cache identisches Verhalten nutzen.
- **Integration (`custom_components/`)** ruft das Add-on über den `AddonClient` auf und enthält keine direkte Grocy- oder Ollama-HTTP-Logik mehr.

### Ingress & Dashboard

- Das Dashboard baut API-URLs robust für Standardbetrieb und Home-Assistant-Ingress (`/api/hassio_ingress/...`).
- Panel-URLs werden normalisiert: absolute Ingress-URLs werden auf den relativen Ingress-Pfad reduziert, Loopback-Ziele (`localhost`, `127.0.0.1`, `::1`) automatisch auf den Standard-Ingress-Fallback gesetzt.
- Produktbilder werden über einen Proxy-Endpunkt bereitgestellt, damit Authentifizierung und gemischte HTTP/HTTPS-Szenarien stabil bleiben.

## Versionen

Aktueller Stand:
- **Add-on:** `6.0.10`
- **Integration:** `2.0.10`

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
- Architektur-Test für Layering-Regeln zwischen `api`, `core`, `ai`, `services` und `custom_components`

## Architektur-Review (aktueller Stand)

Positiv aufgefallen:
- Klare Schichtentrennung zwischen API (`api/`), Orchestrierung (`core/`), KI (`ai/`) und Infrastruktur (`services/`).
- Solide Testabdeckung mit API- und Unit-Tests für Kernflüsse und Hilfslogik.
- Dashboard als Template/Static aufgeteilt, wodurch Frontend-Änderungen strukturiert bleiben.

In diesem Update verbessert:
- Settings laden Standard-Versionen nun automatisch aus `config.json` (Add-on) und `manifest.json` (Integration), wodurch Versionsdrift zwischen Code und Metadaten verhindert wird.
- Ergänzender Unit-Test stellt sicher, dass diese Versionen dauerhaft synchron bleiben.
- Kleine Dokumentations- und Versionspflege für konsistente Release-Stände zwischen Add-on und Integration.

Empfohlene nächste Schritte (optional):
- Integration-Manifest (`manifest.json`) und Add-on-Metadaten (`config.json`) weiterhin gemeinsam versionieren (bereits durch Test abgesichert).
- Optional zentrale API-Fehlerstruktur (einheitliches Error-Schema) einführen, damit Frontend und Integration Fehlermeldungen konsistenter verarbeiten können.

