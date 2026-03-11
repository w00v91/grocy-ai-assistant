# Service Layer (`grocy_ai_assistant/services`)

Infrastructure adapters for external systems.

## Responsibilities

- Handle Grocy HTTP communication and endpoint-specific payload mapping
- Provide caching helpers to reduce redundant remote lookups

## Key files

- `grocy_client.py` – Grocy API adapter
- `location_cache.py` – location ID cache
- `product_image_cache.py` – image URL cache

## Architectural rule

All Grocy-specific HTTP code should stay in this folder to keep boundaries explicit.
