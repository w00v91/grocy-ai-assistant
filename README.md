# Grocy AI Assistant V4

Enterprise-grade AI assistant for Grocy + Home Assistant.

## Features
- Home Assistant Add-on
- Automatic integration registration
- Home Assistant UI dashboard panel
- AI ingredient recognition
- Shopping optimization
- Supermarket data integration (optional)
- Self-learning mappings
- Docker architecture

## Architektur (aufgesplittet)

```text
grocy_ai_assistant/
├── api/
│   ├── main.py                # FastAPI App + Middleware + Startup
│   └── routes.py              # API-Endpunkte
├── ai/
│   └── ingredient_detector.py # Ollama/AI Analyse + Bildgenerierung
├── services/
│   └── grocy_client.py        # Kommunikation mit Grocy API
├── models/
│   └── ingredient.py          # Pydantic Request/Response Modelle
├── config/
│   └── settings.py            # Laden der Add-on Optionen (/data/options.json)
├── custom_components/
│   └── grocy_ai_assistant/    # Home Assistant Integration
├── core/
│   └── engine.py              # Interne Ablauf-Logik
└── db/
    └── ingredients.json
```
