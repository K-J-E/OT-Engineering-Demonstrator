#!/bin/sh
set -eu

SCRIPT_DIRECTORY=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$SCRIPT_DIRECTORY/.." && pwd)
FRONTEND_DIRECTORY="$REPOSITORY_ROOT/app/frontend"
COMMAND=${1:-start}
PYTHON_COMMAND=${OT_DEMO_PYTHON:-}

fail() {
  printf 'Showcase setup error: %s\n' "$1" >&2
  exit 1
}

check_prerequisites() {
  if [ -z "$PYTHON_COMMAND" ]; then
    if command -v python3.13 >/dev/null 2>&1; then
      PYTHON_COMMAND=$(command -v python3.13)
    elif command -v python3 >/dev/null 2>&1; then
      PYTHON_COMMAND=$(command -v python3)
    else
      fail 'Python 3.13 is required.'
    fi
  fi
  [ -x "$PYTHON_COMMAND" ] || fail "Python command is not executable: $PYTHON_COMMAND"
  command -v node >/dev/null 2>&1 || fail 'Node.js 24 is required.'
  command -v npm >/dev/null 2>&1 || fail 'npm 11 is required.'

  PYTHON_VERSION=$("$PYTHON_COMMAND" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  NODE_VERSION=$(node -p 'process.versions.node.split(".")[0]')
  NPM_VERSION=$(npm --version | cut -d. -f1)
  [ "$PYTHON_VERSION" = '3.13' ] || fail "Python 3.13 is required; found $PYTHON_VERSION."
  [ "$NODE_VERSION" = '24' ] || fail "Node.js 24 is required; found major version $NODE_VERSION."
  [ "$NPM_VERSION" = '11' ] || fail "npm 11 is required; found major version $NPM_VERSION."
}

setup() {
  check_prerequisites
  cd "$REPOSITORY_ROOT"
  if [ ! -x .venv/bin/python ]; then
    printf 'Creating the local Python environment…\n'
    "$PYTHON_COMMAND" -m venv .venv
  fi
  printf 'Installing locked backend dependencies…\n'
  .venv/bin/python -m pip install --disable-pip-version-check -r requirements.lock
  printf 'Installing locked frontend dependencies…\n'
  (cd "$FRONTEND_DIRECTORY" && npm ci)
  printf 'Building the reviewer frontend…\n'
  (cd "$FRONTEND_DIRECTORY" && npm run build)
}

ensure_ready() {
  if [ ! -x "$REPOSITORY_ROOT/.venv/bin/python" ] || [ ! -d "$FRONTEND_DIRECTORY/node_modules" ]; then
    setup
  elif [ ! -f "$FRONTEND_DIRECTORY/dist/index.html" ]; then
    (cd "$FRONTEND_DIRECTORY" && npm run build)
  fi
}

case "$COMMAND" in
  setup)
    setup
    ;;
  start)
    ensure_ready
    cd "$REPOSITORY_ROOT"
    PORT=${OT_DEMO_PORT:-8000}
    printf '\nStarting the local simulated demonstrator at http://127.0.0.1:%s\n' "$PORT"
    printf 'Press Ctrl+C for a clean shutdown. No network interface beyond loopback is used.\n\n'
    exec env PYTHONPATH=app/backend .venv/bin/python -m uvicorn ot_demo.api.local:app --host 127.0.0.1 --port "$PORT"
    ;;
  verify)
    ensure_ready
    cd "$REPOSITORY_ROOT"
    .venv/bin/python -m pytest -q
    .venv/bin/python scripts/build_dc006_catalogue.py
    (cd "$FRONTEND_DIRECTORY" && npm test -- --run && npm run build)
    ;;
  reset)
    [ -n "$REPOSITORY_ROOT" ] && [ "$REPOSITORY_ROOT" != '/' ] || fail 'Unsafe repository path.'
    rm -rf "$REPOSITORY_ROOT/app/.runtime" "$REPOSITORY_ROOT/evidence/exports"
    printf 'Local scenario, validation and exported-evidence runtime data cleared. Controlled repository inputs were not changed.\n'
    ;;
  *)
    printf 'Usage: %s [start|setup|verify|reset]\n' "$0" >&2
    exit 2
    ;;
esac
