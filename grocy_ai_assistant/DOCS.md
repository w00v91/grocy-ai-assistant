# Home Assistant Add-on: Grocy AI Assistant

Der **Grocy AI Assistant** ergänzt Grocy in Home Assistant um KI-gestützte Produktanalyse, Produktsuche, Einkaufslisten-Workflows und ein eingebautes Dashboard via Ingress.

Das Add-on kombiniert ein FastAPI-Backend mit einer Home-Assistant-Integration und kann Produktinformationen aus Texten/Bildern auswerten, mit Grocy abgleichen und fehlende Daten wie Nährwerte oder Produktbilder ergänzen.

## Funktionen

- KI-gestützte Analyse von Produkten und Zutaten.
- Dashboard für Suche, Einkaufsliste und Lager-Workflows direkt in Home Assistant.
- Anbindung an eine bestehende Grocy-Instanz per API.
- Optionale Bildanalyse über Ollama/LLaVA.
- Optionale Bildgenerierung für fehlende Produktbilder über OpenAI.
- Einmaliger Info-Sync für bestehende Produkte beim nächsten Add-on-Start.

## Installation

1. Füge dieses Repository als Add-on-Repository in Home Assistant hinzu.
2. Installiere zuerst das benötigte **Grocy** Add-on bzw. stelle sicher, dass deine Grocy-Instanz erreichbar ist.
3. Installiere anschließend **Grocy AI Assistant**.
4. Öffne die Add-on-Konfiguration und trage mindestens die Pflichtwerte ein.
5. Starte das Add-on.
6. Öffne die Weboberfläche über **Öffnen Web UI** oder nutze die Ingress-Seite innerhalb von Home Assistant.
7. Installiere zusätzlich die Home-Assistant-Integration, wenn du das Dashboard als nativen Sidebar-Panel-Eintrag mit direktem Pfad `/grocy-ai` verwenden möchtest.

## Vor der Einrichtung

Für einen sinnvollen Betrieb solltest du folgende Informationen bereithalten:

- die Basis-URL deiner Grocy-API, z. B. `http://homeassistant.local:9192/api`
- einen gültigen Grocy-API-Key
- einen API-Key bzw. ein funktionierendes KI-Backend für deine gewünschte Analyse
- optional einen laufenden Ollama-Dienst mit passenden Modellen
- optional einen OpenAI-API-Key für die Bildgenerierung

## Konfiguration

### Minimalbeispiel

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

### Optionen

| Option | Beschreibung |
| --- | --- |
| `api_key` | API-Schlüssel für die primäre KI-Verarbeitung. |
| `dashboard_polling_interval_seconds` | Aktualisierungsintervall des Dashboards. |
| `notification_global_enabled` | Aktiviert oder deaktiviert Benachrichtigungen global. |
| `grocy.grocy_api_key` | API-Schlüssel deiner Grocy-Instanz. |
| `grocy.grocy_base_url` | Basis-URL deiner Grocy-API. |
| `ollama.ollama_url` | URL zum Ollama-Generate-Endpunkt. |
| `ollama.ollama_model` | Standardmodell für textbasierte Analysen. |
| `ollama.ollama_llava_model` | Vision-Modell für bildbasierte Analysen. |
| `ollama.initial_info_sync` | Ergänzt beim nächsten Start fehlende Nährwerte und geschätzte MHD-Tage. |
| `scanner.scanner_barcode_fallback_seconds` | Zeit bis zur Barcode-Fallback-Logik. |
| `scanner.scanner_llava_min_confidence` | Mindest-Konfidenz für Scanner-Ergebnisse in Prozent. |
| `scanner.scanner_llava_timeout_seconds` | Maximale Wartezeit für LLaVA-Anfragen. |
| `cloud_ai.image_generation_enabled` | Aktiviert die KI-Bildgenerierung für fehlende Produktbilder. |
| `cloud_ai.openai_api_key` | OpenAI-API-Key für die Bildgenerierung. |
| `cloud_ai.openai_image_model` | OpenAI-Modell für die Bildgenerierung, z. B. `gpt-image-1`. |
| `cloud_ai.generate_missing_product_images_on_startup` | Erzeugt fehlende Produktbilder einmalig beim nächsten Start. |
| `debug_mode` | Aktiviert ausführliche Debug-Logs. |

## Nativer Dashboard-Pfad in Home Assistant

Nach dem Einrichten der **Home-Assistant-Integration** wird das Dashboard zusätzlich als nativer Panel-Eintrag registriert. Die Bezeichner sind dabei bewusst identisch gehalten:

- **Titel in der Sidebar:** `Grocy AI`
- **Slug / Zielpfad:** `/grocy-ai`
- **Icon:** `mdi:fridge-outline`

Damit kannst du das Dashboard direkt aus Lovelace, aus Assist-/UI-Aktionen oder aus Skripten öffnen, ohne den Ingress-Pfad manuell zusammensetzen zu müssen.

### Lovelace-Beispiele

```yaml
type: button
name: Grocy AI
icon: mdi:fridge-outline
tap_action:
  action: navigate
  navigation_path: /grocy-ai
```

```yaml
type: tile
entity: sensor.grocy_ai_status
name: Grocy AI Lager
tap_action:
  action: navigate
  navigation_path: /grocy-ai?tab=storage
```

```yaml
type: markdown
content: >
  [Grocy AI Benachrichtigungen](/grocy-ai?tab=notifications)
```

### Deep Links für Tabs

Falls du direkt in einen Bereich springen möchtest, unterstützt das native Panel mehrere URL-Formate:

- `/grocy-ai` oder `/grocy-ai?tab=shopping` → Einkauf
- `/grocy-ai?tab=recipes`, `/grocy-ai#tab=recipes` oder `/grocy-ai/recipes` → Rezepte
- `/grocy-ai?tab=storage`, `/grocy-ai#tab=storage` oder `/grocy-ai/storage` → Lager
- `/grocy-ai?tab=notifications`, `/grocy-ai#tab=notifications` oder `/grocy-ai/notifications` → Benachrichtigungen

Für Home-Assistant-Buttons und `navigate`-Aktionen ist `?tab=...` die empfohlene Variante.

### Schnellaktionen in der nativen UI

Die native Oberfläche unterstützt weiterhin Deep Links auf **Einkauf**, **Rezepte**, **Lager** und **Benachrichtigungen** über den Panel-Pfad `/grocy-ai`.

## API-Typen im Add-on

Das Add-on stellt bewusst zwei API-Ebenen bereit:

- **Integrations-API (`/api/v1/...`)**: stabile, auth-geschützte Endpunkte für die Home-Assistant-Integration und andere technische Clients.
- **Dashboard-/UI-API (`/api/dashboard/...` sowie `/`)**: Endpunkte für Ingress, Web-Dashboard und interaktive UI-Aktionen. Diese API ist stärker auf konkrete Bedienabläufe und UI-Zustände zugeschnitten.

Notification-spezifische Abläufe und Datenmodelle sind separat beschrieben in [docs/notification_architecture.md](../docs/notification_architecture.md) und [NOTIFICATION_DASHBOARD_SPEC.md](custom_components/grocy_ai_assistant/panel/frontend/NOTIFICATION_DASHBOARD_SPEC.md).

## Relevante API-Endpunkte nach Zweck

### Health/Status

- **Integrations-API:** `GET /api/v1/health`, `GET /api/v1/capabilities`, `GET /api/v1/status`
- **Dashboard-/UI-API:** `GET /api/status`, `GET /`

### Einkauf

- **Integrations-API:** `GET /api/v1/shopping-list`, `POST /api/v1/grocy/sync`
- **Dashboard-/UI-API:** `POST /api/dashboard/search`, `GET /api/dashboard/search-variants`, `POST /api/dashboard/add-existing-product`, `GET /api/dashboard/shopping-list`, `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/note`, `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/best-before`, `POST /api/dashboard/shopping-list/item/{shopping_list_id}/best-before/reset`, `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/amount`, `POST /api/dashboard/shopping-list/item/{shopping_list_id}/amount/increment`, `POST /api/dashboard/shopping-list/item/{shopping_list_id}/complete`, `DELETE /api/dashboard/shopping-list/item/{shopping_list_id}`, `POST /api/dashboard/shopping-list/{shopping_list_id}/complete`, `POST /api/dashboard/shopping-list/complete`, `DELETE /api/dashboard/shopping-list/clear`

### Lager

- **Integrations-API:** `GET /api/v1/stock`
- **Dashboard-/UI-API:** `GET /api/dashboard/locations`, `GET /api/dashboard/stock-products`, `POST /api/dashboard/stock-products/{stock_id}/consume`, `PUT /api/dashboard/stock-products/{stock_id}`, `DELETE /api/dashboard/stock-products/{stock_id}`, `GET /api/dashboard/products/{product_id}/nutrition`, `GET /api/dashboard/product-picture`, `POST /api/dashboard/product-picture-cache/refresh`, `DELETE /api/dashboard/products/{product_id}/picture`

### Rezepte

- **Integrations-API:** `GET /api/v1/recipes`
- **Dashboard-/UI-API:** `POST /api/dashboard/recipe-suggestions`, `POST /api/dashboard/recipe/{recipe_id}/add-missing`

### Scanner

- **Integrations-API:** `GET /api/v1/barcode/{barcode}`, `POST /api/v1/scan/image`, `GET /api/v1/last-scan`, `POST /api/v1/catalog/rebuild`
- **Dashboard-/UI-API:** `GET /api/dashboard/barcode/{barcode}`, `POST /api/dashboard/scanner/llava`

### Notifications

- **Integrations-API:** `POST /api/v1/notifications/test`
- **Dashboard-/UI-API:** `GET /api/dashboard/notifications/overview`, `PUT /api/dashboard/notifications/settings`, `PATCH /api/dashboard/notifications/devices/{device_id}`, `POST /api/dashboard/notifications/rules`, `PATCH /api/dashboard/notifications/rules/{rule_id}`, `DELETE /api/dashboard/notifications/rules/{rule_id}`, `POST /api/dashboard/notifications/tests/device`, `POST /api/dashboard/notifications/tests/all`, `POST /api/dashboard/notifications/tests/persistent`

## Hinweise zur Nutzung

- Die Weboberfläche läuft über **Ingress** auf Port `8000`.
- Für die interne Kommunikation anderer Home-Assistant-Apps mit diesem Add-on muss der interne App-Hostname verwendet werden. Bei lokaler Installation lautet dieser Hostname in der Regel `local-grocy-ai-assistant`, also z. B. `http://local-grocy-ai-assistant:8000`.
- Die Home-Assistant-Integration nutzt für Maschinenkommunikation die dedizierte lokale Add-on-API (`/api/v1/...`).
- Das Add-on nutzt die Home-Assistant- und Supervisor-API.
- Optionen wie `generate_missing_product_images_on_startup` und `initial_info_sync` sind für einmalige Startvorgänge gedacht.
- Wenn `image_generation_enabled` deaktiviert ist, werden die OpenAI-Einstellungen im Alltag nicht benötigt.
- Für bildbasierte Erkennung muss dein konfiguriertes Vision-Modell erreichbar sein.

## Bekannte Stolpersteine

- **Grocy nicht erreichbar:** Prüfe `grocy_base_url`, Netzwerkzugriff und den API-Key.
- **Keine Bildanalyse:** Prüfe, ob `ollama_url` erreichbar ist und `ollama_llava_model` existiert.
- **Keine Bildgenerierung:** Aktiviere `image_generation_enabled` und prüfe `openai_api_key` sowie `openai_image_model`.
- **Leere oder langsame UI:** Reduziere bei Bedarf `dashboard_polling_interval_seconds` nicht zu stark und prüfe die Add-on-Logs.

## Support

Wenn etwas nicht funktioniert, prüfe zuerst:

1. die Add-on-Logs,
2. die Konfiguration,
3. die Erreichbarkeit von Grocy, Ollama oder OpenAI,
4. die Projekt-Dokumentation in `README.md` und `CHANGELOG.md`.

## Lizenz

Siehe Repository-Inhalt und Projektdateien für weitere Informationen.
