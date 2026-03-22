#!/usr/bin/env bash
set -Eeuo pipefail

# Codex workspace bootstrap for Grocy AI Assistant
# - always resolves and works from repo root
# - supports being called from any working directory
# - installs HA stack only when compatible / requested

log() { printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
warn() { printf '\n[WARN] %s\n' "$*" >&2; }
die() { printf '\n[ERROR] %s\n' "$*" >&2; exit 1; }

SCRIPT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CALL_PWD="$(pwd)"

find_repo_root() {
  local dir
  for dir in "$CALL_PWD" "$SCRIPT_PATH" "$(dirname "$SCRIPT_PATH")"; do
    if git -C "$dir" rev-parse --show-toplevel >/dev/null 2>&1; then
      git -C "$dir" rev-parse --show-toplevel
      return 0
    fi
  done

  dir="$SCRIPT_PATH"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/grocy_ai_assistant/requirements.txt" ] || [ -f "$dir/README.md" ] || [ -d "$dir/.git" ]; then
      printf '%s\n' "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

REPO_ROOT="$(find_repo_root)" || die "Repo root konnte nicht erkannt werden."
cd "$REPO_ROOT"
log "Arbeite aus Repo-Root: $REPO_ROOT"

VENV_DIR="${VENV_DIR:-$REPO_ROOT/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_HA_STACK="${INSTALL_HA_STACK:-auto}"

REQ_FILE=""
for candidate in \
  "$REPO_ROOT/grocy_ai_assistant/requirements.txt" \
  "$REPO_ROOT/requirements.txt" \
  "$REPO_ROOT/service/requirements.txt"
 do
  if [ -f "$candidate" ]; then
    REQ_FILE="$candidate"
    break
  fi
 done

[ -n "$REQ_FILE" ] || die "Keine requirements.txt gefunden. Erwartet z. B. $REPO_ROOT/grocy_ai_assistant/requirements.txt"
log "Verwende Requirements: $REQ_FILE"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "Python nicht gefunden: $PYTHON_BIN"

if [ ! -d "$VENV_DIR" ]; then
  log "Erstelle virtuelle Umgebung: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

log "Aktualisiere pip/setuptools/wheel"
python -m pip install --upgrade pip setuptools wheel

log "Installiere Projekt-Dependencies"
pip install -r "$REQ_FILE"

log "Installiere Dev-/Test-Tools"
pip install pytest pytest-cov ruff black mypy

PY_MM="$(python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

install_ha_stack=false
case "$INSTALL_HA_STACK" in
  1|true|yes|on)
    install_ha_stack=true
    ;;
  0|false|no|off)
    install_ha_stack=false
    ;;
  auto)
    if python - <<'PY'
import sys
raise SystemExit(0 if (sys.version_info.major, sys.version_info.minor) >= (3,14) else 1)
PY
    then
      install_ha_stack=true
    else
      install_ha_stack=false
    fi
    ;;
  *)
    die "Ungültiger Wert für INSTALL_HA_STACK: $INSTALL_HA_STACK"
    ;;
esac

if [ "$install_ha_stack" = true ]; then
  log "Installiere optionalen Home-Assistant-Teststack"
  pip install homeassistant pytest-homeassistant-custom-component
else
  warn "Überspringe Home-Assistant-Teststack (Python $PY_MM / INSTALL_HA_STACK=$INSTALL_HA_STACK)"
fi

mkdir -p "$REPO_ROOT/reports"

log "Syntax-Sanity-Check"
python -m compileall "$REPO_ROOT" >/dev/null || warn "compileall meldet Probleme"

if [ -d "$REPO_ROOT/tests" ]; then
  log "Pytest Collection-Check"
  pytest --collect-only >/dev/null || warn "pytest --collect-only ist fehlgeschlagen"
fi

cat <<MSG

Setup abgeschlossen.

Repo root: $REPO_ROOT
Virtualenv: $VENV_DIR
Requirements: $REQ_FILE
HA stack: $( [ "$install_ha_stack" = true ] && echo installiert || echo übersprungen )

Nächste Befehle:
  source "$VENV_DIR/bin/activate"
  pytest
  ruff check .
  black --check .

MSG
