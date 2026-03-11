# Grocy AI Assistant

KI-gestütztes Home-Assistant-Add-on mit FastAPI-Backend und zugehöriger Custom Integration für Grocy.

## Ziel des Projekts

Das Projekt erkennt Produkte/Zutaten über ein KI-Modell (Ollama), sucht oder erstellt passende Produkte in Grocy und kann sie direkt auf die Einkaufsliste setzen.

## Komponenten

- **Add-on Backend (FastAPI):** API, Dashboard und Orchestrierung
- **KI-Layer:** Prompting und Ergebnis-Normalisierung
- **Service-Layer:** Gekapselte Grocy-HTTP-Kommunikation
- **Custom Integration:** Home-Assistant-Entities + Add-on-Anbindung

## Verzeichnisstruktur

```text
grocy_ai_assistant/
├── api/                                   # FastAPI App, Routen, Dashboard
├── ai/                                    # KI-Erkennung (Ollama)
├── config/                                # Laufzeit-Settings
├── core/                                  # Workflow-Orchestrierung
├── custom_components/grocy_ai_assistant/  # Home Assistant Integration
├── db/                                    # Persistente JSON-Daten
├── models/                                # Pydantic-Modelle
└── services/                              # Grocy Adapter + Caches
```

Zusätzliche Layer-Dokumentation liegt jeweils in:

- `grocy_ai_assistant/api/README.md`
- `grocy_ai_assistant/ai/README.md`
- `grocy_ai_assistant/core/README.md`
- `grocy_ai_assistant/services/README.md`
- `grocy_ai_assistant/custom_components/grocy_ai_assistant/README.md`

## Voraussetzungen

- Python **3.11+**
- Erreichbarer Grocy-Server
- Optional Ollama-Server

## Installation & Start

```bash
pip install -r requirements.txt
python -m grocy_ai_assistant.api.main
```

Standardmäßig läuft die API dann unter `http://localhost:8000`.

## Wichtige Endpunkte

- `GET /api/status` – Health, Versionen, Restart-Hinweise
- `POST /api/analyze_product` – KI-Analyse eines Produktnamens
- `POST /api/dashboard/search` – Such-/Anlage-Workflow inkl. Einkaufsliste
- `GET /api/dashboard/shopping-list` – aktuelle Grocy-Einkaufsliste
- `GET /` – Dashboard

## Architekturprinzipien

- **API bleibt dünn:** Validierung, Response-Mapping, keine Business-Logik.
- **Orchestrierung in `core/`:** End-to-End-Workflows für Analyse und Grocy-Aktionen.
- **Externe Kommunikation in `services/`:** Grocy-spezifische HTTP-Details zentralisiert.
- **KI strikt in `ai/`:** Prompting/Parsing, keine API-Routen.
- **Integration entkoppelt:** Home Assistant spricht ausschließlich mit dem Add-on, nicht direkt mit Grocy.

## Versionierung

Add-on und Custom Integration werden **immer gemeinsam** versioniert.

Aktueller Stand:

- **Add-on:** `7.0.5`
- **Integration:** `7.0.5`

## Qualitätssicherung

```bash
pytest
ruff check .
black --check .
```

## Ergebnis der aktuellen Projektprüfung

Im Rahmen dieser Prüfung wurden folgende strukturelle Verbesserungen umgesetzt:

- Root-`requirements.txt` ergänzt (delegiert auf `grocy_ai_assistant/requirements.txt`), damit Standard-Installationskommando konsistent funktioniert.
- Architekturbeschreibung gestrafft und Layer-Verantwortung pro Verzeichnis dokumentiert.
- Teilbereichs-READMEs für API, AI, Core, Services und HA-Integration ergänzt.
- Versionsstände synchron auf `7.0.5` aktualisiert.
