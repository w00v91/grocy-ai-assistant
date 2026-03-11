# API Layer (`grocy_ai_assistant/api`)

FastAPI entrypoint and HTTP surface for the add-on.

## Responsibilities

- Define API routes and request/response contracts
- Serve dashboard template and static assets
- Translate domain/service errors into stable HTTP responses

## Key files

- `main.py` – App bootstrap and middleware setup
- `routes.py` – API endpoints (`/api/*`, dashboard, proxy routes)
- `errors.py` – Shared API error schema helpers
- `templates/` + `static/` – Dashboard UI

## Architectural rule

No direct Grocy API calls or Ollama inference logic in this folder.
Use `core/engine.py` for orchestration and `services/` for outbound Grocy communication.
