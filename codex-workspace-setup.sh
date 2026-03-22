#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

log() {
  printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

log "Validating base tools"
need_cmd "$PYTHON_BIN"
need_cmd git

log "Creating virtual environment in $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

log "Upgrading pip/setuptools/wheel"
python -m pip install --upgrade pip setuptools wheel

log "Installing project runtime dependencies"
pip install -r grocy_ai_assistant/requirements.txt

log "Installing development and test tooling"
pip install \
  pytest \
  pytest-asyncio \
  pytest-cov \
  ruff \
  black \
  mypy \
  httpx \
  requests \
  aiohttp \
  respx \
  fastapi \
  uvicorn \
  python-dotenv \
  pydantic \
  rapidfuzz

log "Installing optional Home Assistant integration test stack"
pip install \
  "homeassistant>=2026.3.0" \
  "pytest-homeassistant-custom-component>=0.13" || true

log "Installing repo in editable mode"
pip install -e . || true

log "Preparing common runtime directories"
mkdir -p .pytest_cache .mypy_cache reports tmp .codex-work

log "Writing local environment helper"
cat > .env.codex.local <<'ENVEOF'
# Local helper values for Codex / manual runs
PYTHONPATH=.
PYTEST_ADDOPTS=-ra
ENVEOF

log "Printing versions"
python --version
pytest --version
ruff --version || true
black --version || true
mypy --version || true

log "Sanity checks"
python -m compileall grocy_ai_assistant >/dev/null
pytest --collect-only -q >/dev/null

cat <<'DONE'

Workspace bootstrap complete.

Recommended commands:
  source .venv/bin/activate
  pytest
  ruff check .
  black --check .
  python -m grocy_ai_assistant.api.main

Notes:
- This script installs more than the current repo strictly needs so Codex can also run future HA integration tests.
- If Home Assistant dependency resolution ever becomes too heavy, move the HA test stack into a separate script.
DONE
