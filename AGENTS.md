# Grocy AI Assistant

AI service that detects ingredients from images and syncs them to Grocy.

## Project Structure

grocy_ai_assistant/
  api/                 FastAPI server
  ai/                  AI ingredient detection
  services/            Grocy API integration
  custom_components/   Home Assistant integration

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
- Bump always both versions on changes

## Tasks Codex may perform

- implement new API endpoints
- add AI detection models
- improve Grocy integration
- add tests
