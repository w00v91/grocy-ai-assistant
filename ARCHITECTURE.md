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
  - Home-Assistant-seitige Integration (Panel, Sensor, Add-on Kommunikation).

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
