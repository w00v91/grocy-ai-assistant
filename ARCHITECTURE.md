# Architekturübersicht

Dieses Dokument beschreibt die fachliche und technische Aufteilung des Projekts.

## Schichtenmodell

```text
grocy_ai_assistant/
├── api/            HTTP-Adapter (FastAPI, Dashboard, Request/Response)
├── core/           Orchestrierung und domänennahe Hilfslogik
├── ai/             KI-gestützte Auswertung (Ollama, Prompting)
├── services/       Infrastrukturadapter (Grocy API, Caches)
├── models/         Pydantic-Schemas und DTOs
├── config/         Konfiguration/Settings
└── custom_components/
    └── grocy_ai_assistant/  Home Assistant Integration (Consumer des Add-ons)
```

## Verantwortlichkeiten

- `api/`
  - Definiert Endpunkte, HTTP-Fehler, Template-Rendering.
  - Sollte **keine** Grocy-Details oder KI-Promptlogik enthalten.
- `core/`
  - Koordiniert Abläufe zwischen API, KI und Services.
  - Enthält wiederverwendbare Business-Helfer.
- `ai/`
  - Kapselt Modellerkennung, Prompts und KI-spezifische Verarbeitung.
- `services/`
  - Kapselt externe Kommunikation mit Grocy (inkl. Caches/HTTP-Zugriff).
- `custom_components/`
  - Home-Assistant-seitige Integration (Config Flow, Sensoren, Buttons, Services, Add-on Kommunikation).

## Add-on ↔ Integration

- Das Add-on ist der laufende Backend-Service und stellt eine dedizierte HTTP-API unter `/api/v1/...` bereit.
- Die Integration nutzt diese Service-API für Status, Scan, Sync und Katalogaktionen.
- Dashboard-/Ingress-Endpunkte bleiben der Weboberfläche vorbehalten.
- Direkte Python-Imports zwischen Add-on und Integration sind nicht vorgesehen.


## Notification-Subsystem (Home-Assistant-seitig)

Für produktionsreife Benachrichtigungen existiert im Integrationsmodul eine dedizierte Pipeline:

- `notify_events.py`: kanonische fachliche Events (`item_added`, `shopping_due`, …).
- `notify_rules.py`: Rule Engine (Aktivierung, Zielauflösung, Conditions, Quiet Hours, Cooldown/Deduplizierung).
- `notify_dispatcher.py`: Zustellung über `notify.mobile_app_*` und `persistent_notification.create`.
- `notify_store.py`: persistente Ablage von Regeln/Zielen/Preferences/Historie via HA-`.storage` inkl. Versionierung.
- `services.py`: Orchestrator + Home-Assistant-Services für Event-Ingestion und Testcenter.

Die fachliche Event-Erzeugung bleibt dabei strikt von der Zustellung getrennt.

## Architektur-Regeln (automatisiert)

Ein Architekturtest validiert Layer-Abhängigkeiten:

- `api` darf nicht auf `custom_components` zugreifen.
- `ai` darf nicht auf `api`, `custom_components`, `services` zugreifen.
- `core` darf nicht auf `api`, `custom_components` zugreifen.
- `services` darf nicht auf `api`, `custom_components` zugreifen.
- `custom_components` darf nicht auf `ai`, `services` zugreifen.

Datei: `tests/architecture/test_layering.py`

## Empfohlene Erweiterungsstrategie

1. Neue Endpunkte zuerst in `api/routes.py` definieren.
2. Prozesslogik in `core/` auslagern (statt im Endpoint zu belassen).
3. Externe Calls als Adapter in `services/` kapseln.
4. Für KI-Features ausschließlich `ai/` erweitern.
5. Für jede neue Schichtgrenze einen Test ergänzen.

## Wartungsprinzipien

- Utility-Funktionen mit zentraler Bedeutung (z. B. Barcode-Normalisierung) dürfen nur einmal pro Modul definiert werden.
- Gleichartige Endpoint-Flows (`/api/dashboard/search` und `/api/dashboard/search-variants`) sollen gemeinsame Helper (`_build_fallback_variants`, `_extract_amount_prefixed_product_input`) nutzen.
- Bei Verhaltensänderungen in Query-Parametern (z. B. `include_ai`) müssen API-Tests explizit beide Modi abdecken.
