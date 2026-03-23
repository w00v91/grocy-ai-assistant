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
├── ARCHITECTURE.md
├── README.md
├── grocy_ai_assistant/CHANGELOG.md
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

`grocy_ai_assistant/api/routes.py` ist die maßgebliche Quelle für die tatsächlich bereitgestellten Routen. Die HTTP-Oberflächen lassen sich in zwei Familien aufteilen:

- **Integrations-API (`/api/v1/...`)** für Home-Assistant-Integration, Automationen und andere maschinenlesbare Clients.
- **Dashboard-/UI-API (`/api/dashboard/...` und `/`)** für das eingebaute Web-Dashboard, inklusive formularnaher Aktionen und UI-spezifischer Hilfsrouten.

### Health/Status

#### Integrations-API (`/api/v1/...`)

- `GET /api/v1/health` – schlanker Health-Check mit Add-on- und Mindest-Integrationsversion
- `GET /api/v1/capabilities` – Feature-Flags, dokumentierte Defaults und verfügbare `/api/v1/...`-Endpunkte
- `GET /api/v1/status` – detaillierter Laufzeitstatus inklusive Kompatibilitätsprüfung Integration ↔ Add-on

#### Dashboard-/UI-API (`/api/dashboard/...`)

- `GET /api/status` – UI-naher Statusendpunkt für Dashboard/Ingress
- `GET /` – Dashboard-Startseite

### Einkauf

#### Integrations-API (`/api/v1/...`)

- `GET /api/v1/shopping-list` – aktuelle Einkaufsliste abrufen
- `POST /api/v1/grocy/sync` – Produkt analysieren, ggf. anlegen und zur Einkaufsliste hinzufügen

#### Dashboard-/UI-API (`/api/dashboard/...`)

- `POST /api/dashboard/search` – Produktsuche/-anlage mit direkter Einkaufslisten-Aktion
- `GET /api/dashboard/search-variants` – Varianten-/Fallback-Suche für uneindeutige Produkte
- `POST /api/dashboard/add-existing-product` – vorhandenes Grocy-Produkt direkt zur Einkaufsliste hinzufügen
- `GET /api/dashboard/shopping-list` – Einkaufsliste für das Dashboard laden
- `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/note` – Notiz eines Einkaufslisteneintrags aktualisieren
- `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/best-before` – MHD eines Einkaufslisteneintrags setzen
- `POST /api/dashboard/shopping-list/item/{shopping_list_id}/best-before/reset` – MHD eines Einkaufslisteneintrags zurücksetzen
- `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/amount` – Menge eines Einkaufslisteneintrags setzen
- `POST /api/dashboard/shopping-list/item/{shopping_list_id}/amount/increment` – Menge inkrementieren
- `POST /api/dashboard/shopping-list/item/{shopping_list_id}/complete` – einzelnen Einkaufslisteneintrag abschließen
- `DELETE /api/dashboard/shopping-list/item/{shopping_list_id}` – einzelnen Einkaufslisteneintrag löschen
- `POST /api/dashboard/shopping-list/{shopping_list_id}/complete` – konkrete Grocy-Einkaufsliste abschließen
- `POST /api/dashboard/shopping-list/complete` – Standard-Einkaufsliste abschließen
- `DELETE /api/dashboard/shopping-list/clear` – Einkaufsliste leeren

### Lager

#### Integrations-API (`/api/v1/...`)

- `GET /api/v1/stock` – Lagerübersicht, optional filterbar per `location_ids`, `include_all_products` und `q`

#### Dashboard-/UI-API (`/api/dashboard/...`)

- `GET /api/dashboard/locations` – verfügbare Lagerorte laden
- `GET /api/dashboard/stock-products` – Lagerprodukte für das Dashboard abrufen
- `POST /api/dashboard/stock-products/{stock_id}/consume` – Bestand verbrauchen
- `PUT /api/dashboard/stock-products/{stock_id}` – Bestandseintrag aktualisieren
- `DELETE /api/dashboard/stock-products/{stock_id}` – Bestandseintrag löschen
- `GET /api/dashboard/products/{product_id}/nutrition` – Produkt-Nährwerte für Detailansichten laden
- `GET /api/dashboard/product-picture` – Produktbild via Dashboard-Proxy ausliefern
- `POST /api/dashboard/product-picture-cache/refresh` – Bild-Cache aktualisieren
- `DELETE /api/dashboard/products/{product_id}/picture` – Produktbild entfernen

### Rezepte

#### Integrations-API (`/api/v1/...`)

- `GET /api/v1/recipes` – Rezeptvorschläge auf Basis von Produkt- und Lagerortfiltern sowie optional nahendem MHD

#### Dashboard-/UI-API (`/api/dashboard/...`)

- `POST /api/dashboard/recipe-suggestions` – Rezeptvorschläge für das Dashboard laden
- `POST /api/dashboard/recipe/{recipe_id}/add-missing` – fehlende Rezeptzutaten zur Einkaufsliste hinzufügen

### Scanner

#### Integrations-API (`/api/v1/...`)

- `GET /api/v1/barcode/{barcode}` – Barcode-Lookup gegen OpenFoodFacts/Grocy
- `POST /api/v1/scan/image` – Bildanalyse via LLaVA
- `GET /api/v1/last-scan` – zuletzt gespeichertes Scanner-Ergebnis abrufen
- `POST /api/v1/catalog/rebuild` – Katalog-/Cache-Neuaufbau für Such-/Scanner-Workflows

#### Dashboard-/UI-API (`/api/dashboard/...`)

- `GET /api/dashboard/barcode/{barcode}` – Barcode-Lookup für das Dashboard
- `POST /api/dashboard/scanner/llava` – bildbasierte Produkterkennung für den Scanner-Dialog

### Notifications

#### Integrations-API (`/api/v1/...`)

- `POST /api/v1/notifications/test` – persistente Test-Benachrichtigung auslösen

#### Dashboard-/UI-API (`/api/dashboard/...`)

- `GET /api/dashboard/notifications/overview` – Notification-Übersicht für den aktuellen Nutzer laden
- `PUT /api/dashboard/notifications/settings` – Notification-Einstellungen aktualisieren
- `PATCH /api/dashboard/notifications/devices/{device_id}` – Zielgerät aktivieren/deaktivieren
- `POST /api/dashboard/notifications/rules` – Notification-Regel anlegen
- `PATCH /api/dashboard/notifications/rules/{rule_id}` – Notification-Regel aktualisieren
- `DELETE /api/dashboard/notifications/rules/{rule_id}` – Notification-Regel löschen
- `POST /api/dashboard/notifications/tests/device` – Test an ein einzelnes Gerät senden
- `POST /api/dashboard/notifications/tests/all` – Test an alle aktiven Geräte senden
- `POST /api/dashboard/notifications/tests/persistent` – persistente Test-Benachrichtigung senden

Für Details zur Notification-Architektur und zum Dashboard-Verhalten siehe [docs/notification_architecture.md](docs/notification_architecture.md) sowie [grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/NOTIFICATION_DASHBOARD_SPEC.md](grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/NOTIFICATION_DASHBOARD_SPEC.md).

## Konfiguration

Primär via Add-on-Optionen (`/data/options.yaml`) und Umgebungsvariablen.

Aktuelles Minimalbeispiel im Add-on-Schema:

```yaml
api_key: "DEIN_KI_KEY"
notification_global_enabled: true
dashboard_polling_interval_seconds: 5
grocy:
  grocy_api_key: "DEIN_GROCY_KEY"
  grocy_base_url: "http://homeassistant.local:9192/api"
ollama:
  ollama_url: "http://76e18fb5_ollama:11434/api/generate"
  ollama_model: "llama3"
  ollama_llava_model: "llava"
  initial_info_sync: false
scanner:
  scanner_barcode_fallback_seconds: 5
  scanner_llava_min_confidence: 75
  scanner_llava_timeout_seconds: 45
cloud_ai:
  image_generation_enabled: false
  openai_api_key: "DEIN_OPENAI_KEY"
  openai_image_model: "gpt-image-1"
  generate_missing_product_images_on_startup: false
debug_mode: false
```

Wesentliche Schlüsselgruppen:

- global: `api_key`, `notification_global_enabled`, `dashboard_polling_interval_seconds`, `debug_mode`
- `grocy.*`: Grocy-API-Key und Basis-URL
- `ollama.*`: Text-/Vision-Modelle und Initial-Sync
- `scanner.*`: Barcode-/LLaVA-Timeouts und Schwellenwerte
- `cloud_ai.*`: optionale OpenAI-Bildgenerierung

## Native Panel-URL in Home Assistant

Die Integration registriert das Dashboard als **nativen Home-Assistant-Panel-Eintrag** mit konsistenten Bezeichnern:

- **Titel:** `Grocy AI`
- **Slug / URL-Pfad:** `/grocy-ai`
- **Sidebar-Icon:** `mdi:fridge-outline`

Damit kann der Bereich nicht nur über die Sidebar, sondern auch direkt aus **Lovelace-Dashboards, Chips, Buttons, Skripten und Automationen** geöffnet werden.

### Lovelace-Navigation direkt auf das Panel

```yaml
type: button
name: Grocy AI öffnen
icon: mdi:fridge-outline
tap_action:
  action: navigate
  navigation_path: /grocy-ai
```

```yaml
type: entities
entities:
  - type: button
    name: Grocy AI Rezepte
    icon: mdi:chef-hat
    tap_action:
      action: navigate
      navigation_path: /grocy-ai?tab=recipes
```

### Deep Links für Tabs

Der native Panel-Container wertet Tabs jetzt direkt aus der URL aus. Unterstützte Varianten sind:

- `/grocy-ai` → Standardansicht **Einkauf**
- `/grocy-ai?tab=shopping`
- `/grocy-ai?tab=recipes`
- `/grocy-ai?tab=storage`
- `/grocy-ai?tab=notifications`
- `/grocy-ai#tab=recipes`
- `/grocy-ai/recipes`

Die Query-Variante (`?tab=...`) ist für Home-Assistant-Navigation in der Regel die robusteste Form.

## Kopplung Add-on ↔ Integration

- Das Add-on hostet den eigentlichen Backend-Service auf Port `8000`.
- Die Home-Assistant-Integration spricht primär die dedizierte `/api/v1/...`-API an.
- Ingress (`/api/hassio_ingress/...`) bleibt für die Weboberfläche/Panel-Nutzung vorgesehen.
- Die Integration handelt die interne API-Kommunikation automatisch über Supervisor-Metadaten sowie bekannte Home-Assistant-App-Hostnamen aus; eine manuelle API-Basis-URL ist dafür nicht mehr erforderlich.
- Add-on-seitige Home-Assistant-Aufrufe laufen nur bei Bedarf über den Supervisor-Proxy.

## Architektur- und Struktur-Checks

Zur laufenden Qualitätssicherung gelten folgende Leitlinien im Projekt:

- Layering wird über `tests/architecture/test_layering.py` automatisiert geprüft.
- API-Logik soll Orchestrierung/Helferfunktionen wiederverwenden, statt gleiche Logik mehrfach zu implementieren.
- Änderungen an Laufzeitverhalten müssen durch API-/Unit-Tests abgesichert sein.

## Entwicklung

Vor Checks mit Home-Assistant-Bezug sollte zuerst das Workspace-Setup laufen:

```bash
INSTALL_HA_STACK=1 bash scripts/codex-workspace-setup.sh
```

### Vollständige lokale Prüfung

```bash
source .venv/bin/activate && pytest
source .venv/bin/activate && ruff check .
source .venv/bin/activate && black --check .
source .venv/bin/activate && python -m compileall grocy_ai_assistant tests
node --test tests/frontend/*.mjs
```

### Einzelkommandos

```bash
pytest
ruff check .
black .
```

## Kompatibilität

- Python: `3.11+`
- Home Assistant: Die Testumgebung in diesem Repository nutzt aktuell `Home Assistant 2026.2.x`.
- Add-on und Integration sollten versionsgleich betrieben werden.

## Versionierung

Dieses Repository enthält zwei relevante Versionsdomänen:

- Add-on-Metadaten in `grocy_ai_assistant/config.yaml`
- Integrationsversion in `grocy_ai_assistant/custom_components/grocy_ai_assistant/manifest.json`

Zusätzlich nutzt die Integration eine Konstante in `const.py`, die synchron zur Manifest-Version gehalten wird.

Aktueller Stand:

- **Add-on (`grocy_ai_assistant/config.yaml`):** `8.0.30`
- **Integration (`grocy_ai_assistant/custom_components/grocy_ai_assistant/manifest.json`):** `8.0.30`
- **Integrationskonstante (`grocy_ai_assistant/custom_components/grocy_ai_assistant/const.py`):** `8.0.30`

### Maintainer-Workflow

- Version-Bump und zugehöriger Changelog-Eintrag müssen immer im selben Commit bzw. derselben Änderung gemeinsam erfolgen.
- Vor einem Release muss die Spitzenversion in `grocy_ai_assistant/CHANGELOG.md` mit `grocy_ai_assistant/config.yaml`, `grocy_ai_assistant/custom_components/grocy_ai_assistant/manifest.json` und `grocy_ai_assistant/custom_components/grocy_ai_assistant/const.py` übereinstimmen.

## Add-on-Dokumentation

Eine Home-Assistant-konforme Add-on-Benutzerdokumentation findest du in `grocy_ai_assistant/DOCS.md`.

## Changelog

Änderungen werden in [grocy_ai_assistant/CHANGELOG.md](grocy_ai_assistant/CHANGELOG.md) gepflegt.
