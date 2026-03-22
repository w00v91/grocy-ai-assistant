# Grocy AI Assistant

AI service that detects ingredients from images and syncs them to Grocy.

## Project Structure

grocy_ai_assistant/
  api/                 FastAPI server
  ai/                  AI ingredient detection
  services/            Grocy API integration
  custom_components/   Home Assistant integration

## Setup
Before running tests or editing architecture-sensitive code, run:

  ### HA-Stack explizit aus
    INSTALL_HA_STACK=0 bash scripts/codex-workspace-setup.sh

  ### HA-Stack erzwingen (nur sinnvoll mit Python >= 3.14.2)
    INSTALL_HA_STACK=1 bash scripts/codex-workspace-setup.sh

## Primary checks
    source .venv/bin/activate && pytest
    source .venv/bin/activate && ruff check .
    source .venv/bin/activate && black --check .

## Commands

install:
    
    pip install -r requirements.txt

start:
    
    python -m grocy_ai_assistant.api.main

test:
    
    pytest

lint:
    
    ruff check .

format:
    
    black .

## Rules

- Use FastAPI for all API endpoints
- Keep AI code inside /ai
- Grocy communication only in /services
- Home Assistant integration must stay in /custom_components
- Create a Changelog when performing changes
- Update version at least in config.json on changes

