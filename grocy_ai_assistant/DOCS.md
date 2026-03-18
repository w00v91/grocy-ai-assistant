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
grocy_api_key: "DEIN_GROCY_KEY"
grocy_base_url: "http://homeassistant.local:9192/api"
ollama_url: "http://76e18fb5_ollama:11434/api/generate"
ollama_model: "llama3"
ollama_llava_model: "llava"
scanner_barcode_fallback_seconds: 5
scanner_llava_min_confidence: 75
scanner_llava_timeout_seconds: 45
dashboard_polling_interval_seconds: 5
notification_global_enabled: true
image_generation_enabled: false
openai_api_key: "DEIN_OPENAI_KEY"
openai_image_model: "gpt-image-1"
generate_missing_product_images_on_startup: false
initial_info_sync: false
debug_mode: false
```

### Optionen

| Option | Beschreibung |
| --- | --- |
| `api_key` | API-Schlüssel für die primäre KI-Verarbeitung. |
| `grocy_api_key` | API-Schlüssel deiner Grocy-Instanz. |
| `grocy_base_url` | Basis-URL deiner Grocy-API. |
| `ollama_url` | URL zum Ollama-Generate-Endpunkt. |
| `ollama_model` | Standardmodell für textbasierte Analysen. |
| `ollama_llava_model` | Vision-Modell für bildbasierte Analysen. |
| `scanner_barcode_fallback_seconds` | Zeit bis zur Barcode-Fallback-Logik. |
| `scanner_llava_min_confidence` | Mindest-Konfidenz für Scanner-Ergebnisse in Prozent. |
| `scanner_llava_timeout_seconds` | Maximale Wartezeit für LLaVA-Anfragen. |
| `dashboard_polling_interval_seconds` | Aktualisierungsintervall des Dashboards. |
| `notification_global_enabled` | Aktiviert oder deaktiviert Benachrichtigungen global. |
| `image_generation_enabled` | Aktiviert die KI-Bildgenerierung für fehlende Produktbilder. |
| `openai_api_key` | OpenAI-API-Key für die Bildgenerierung. |
| `openai_image_model` | OpenAI-Modell für die Bildgenerierung, z. B. `gpt-image-1`. |
| `generate_missing_product_images_on_startup` | Erzeugt fehlende Produktbilder einmalig beim nächsten Start. |
| `initial_info_sync` | Ergänzt beim nächsten Start fehlende Nährwerte und geschätzte MHD-Tage. |
| `debug_mode` | Aktiviert ausführliche Debug-Logs. |

## Hinweise zur Nutzung

- Die Weboberfläche läuft über **Ingress** auf Port `8000`.
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
