# Grocy AI Assistant

Grocy AI Assistant ist ein Home-Assistant-Add-on mit FastAPI-Backend und passender Home-Assistant-Integration.
Das Projekt analysiert Produktinformationen (z. B. per KI), gleicht sie mit Grocy ab und unterstützt Workflows wie Produktsuche, Produktanlage und Einkaufsliste.

## Ziel des Projekts

- Produktdaten intelligent verarbeiten und normalisieren.
- Grocy-Operationen sauber kapseln (Service-Layer).
- Home Assistant mit stabilen Sensoren, Panel und API-Anbindung versorgen.
- Dashboard und API in einem wartbaren FastAPI-Service bereitstellen.

## Architektur auf einen Blick

Die Schichten sind bewusst getrennt:

- `grocy_ai_assistant/api`: HTTP-Endpunkte, Fehlerbehandlung, Dashboard-Template/Assets.
- `grocy_ai_assistant/core`: Orchestrierung und zentrale Hilfslogik.
- `grocy_ai_assistant/ai`: KI-Logik (z. B. IngredientDetector).
- `grocy_ai_assistant/services`: Externe Integrationen (insb. Grocy-Client, Caches).
- `grocy_ai_assistant/custom_components/grocy_ai_assistant`: Home-Assistant-Integration.

Weitere Details: [ARCHITECTURE.md](ARCHITECTURE.md)

## Projektstruktur

```text
.
├── grocy_ai_assistant/
│   ├── api/
│   ├── ai/
│   ├── config/
│   ├── core/
│   ├── custom_components/grocy_ai_assistant/
│   ├── db/
│   ├── models/
│   └── services/
├── tests/
├── CHANGELOG.md
├── ARCHITECTURE.md
├── README.md
└── grocy_ai_assistant/DOCS.md
```

## Voraussetzungen

- Python 3.11+
- Laufendes Grocy-System
- Optional: Ollama für KI-Funktionen

## Installation

```bash
pip install -r grocy_ai_assistant/requirements.txt
```

## Start

```bash
python -m grocy_ai_assistant.api.main
```

Standardmäßig läuft der Service dann auf `http://localhost:8000`.

## Wichtige API-Endpunkte

### Integrations-/Service-API

- `GET /api/v1/health` – schlanker Health-Check für die Integration
- `GET /api/v1/capabilities` – unterstützte Backend-Funktionen und Defaults
- `GET /api/v1/status` – Status, Versionen, Kompatibilitätsprüfung Integration ↔ Add-on
- `POST /api/v1/scan/image` – Bildanalyse via LLaVA
- `POST /api/v1/grocy/sync` – Produktanalyse und Grocy-Synchronisierung
- `POST /api/v1/catalog/rebuild` – Katalog-/Cache-Aktualisierung
- `POST /api/v1/notifications/test` – Test einer persistenten Benachrichtigung

### Dashboard-/UI-API

- `POST /api/dashboard/search` – Dashboard-Produktsuche/Anlage inkl. Einkaufsliste
- `GET /api/dashboard/shopping-list` – Einkaufsliste laden
- `GET /` – Dashboard

## Konfiguration

Primär via Add-on-Optionen (`/data/options.json`) und Umgebungsvariablen.

Wesentliche Schlüssel:

- `api_key`
- `grocy_api_key`
- `grocy_base_url`
- `ollama_url`
- `ollama_model`
- `ollama_llava_model`
- `scanner_barcode_fallback_seconds`
- `scanner_llava_min_confidence`

## Kopplung Add-on ↔ Integration

- Das Add-on hostet den eigentlichen Backend-Service auf Port `8000`.
- Die Home-Assistant-Integration spricht primär die dedizierte `/api/v1/...`-API an.
- Ingress (`/api/hassio_ingress/...`) bleibt für die Weboberfläche/Panel-Nutzung vorgesehen.
- Add-on-seitige Home-Assistant-Aufrufe laufen nur bei Bedarf über den Supervisor-Proxy.

## Architektur- und Struktur-Checks

Zur laufenden Qualitätssicherung gelten folgende Leitlinien im Projekt:

- Layering wird über `tests/architecture/test_layering.py` automatisiert geprüft.
- API-Logik soll Orchestrierung/Helferfunktionen wiederverwenden, statt gleiche Logik mehrfach zu implementieren.
- Änderungen an Laufzeitverhalten müssen durch API-/Unit-Tests abgesichert sein.

## Entwicklung

### Tests

```bash
pytest
```

### Linting

```bash
ruff check .
```

### Formatierung

```bash
black .
```

## Versionierung

Dieses Repository enthält zwei relevante Versionsdomänen:

- Add-on-Metadaten in `grocy_ai_assistant/config.yaml`
- Integrationsversion in `grocy_ai_assistant/custom_components/grocy_ai_assistant/manifest.json`

Zusätzlich nutzt die Integration eine Konstante in `const.py`, die synchron zur Manifest-Version gehalten wird.

Aktueller Stand:

- **Add-on:** `7.2.29`
- **Integration:** siehe `manifest.json` der Home-Assistant-Integration

## Add-on-Dokumentation

Eine Home-Assistant-konforme Add-on-Benutzerdokumentation findest du in `grocy_ai_assistant/DOCS.md`.

## Changelog

Änderungen werden in [CHANGELOG.md](CHANGELOG.md) gepflegt.
