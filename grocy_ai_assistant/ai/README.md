# AI Layer (`grocy_ai_assistant/ai`)

Contains model-facing logic for ingredient/product detection.

## Responsibilities

- Build and execute prompts for Ollama
- Parse and normalize model output into structured payloads

## Key file

- `ingredient_detector.py` – detector abstraction used by the engine

## Architectural rule

Keep model-specific code here. Route handlers and Grocy-specific persistence stay outside this folder.
