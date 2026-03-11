# Core Layer (`grocy_ai_assistant/core`)

Domain orchestration and shared workflow logic.

## Responsibilities

- Coordinate AI detection and Grocy product/search workflow
- Keep application flow independent from web framework details
- Provide shared helpers used by multiple layers

## Key files

- `engine.py` – central workflow orchestration
- `picture_urls.py` – consistent product image URL normalization

## Architectural rule

This layer may depend on `ai/`, `services/`, and `models/`, but should not import FastAPI route objects.
