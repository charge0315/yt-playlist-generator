#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "[ERR]  line $LINENO: $BASH_COMMAND" >&2' ERR

INFO() { echo -e "\033[36m[INFO]\033[0m $*"; }
OK()   { echo -e "\033[32m[OK]  \033[0m $*"; }
WARN() { echo -e "\033[33m[WARN]\033[0m $*"; }
ERR()  { echo -e "\033[31m[ERR] \033[0m $*"; }

usage() {
  cat <<USAGE
Usage: bash ./setup.sh [--recreate] [--run]

Options:
  --recreate   Recreate .venv from scratch
  --run        Run scripts/main.py after setup
  -h, --help   Show this help
USAGE
}

RECREATE=false
RUN_AFTER=false
for arg in "$@"; do
  case "$arg" in
    --recreate) RECREATE=true ;;
    --run) RUN_AFTER=true ;;
    -h|--help) usage; exit 0 ;;
    *) ERR "Unknown option: $arg"; usage; exit 2 ;;
  esac
done

# Repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
INFO "Repository root: $SCRIPT_DIR"

# Find Python
if command -v python3 >/dev/null 2>&1; then
  PY=python3
  OK "Using Python via 'python3'"
elif command -v python >/dev/null 2>&1; then
  PY=python
  OK "Using Python via 'python'"
else
  ERR "Python 3.x not found. Please install Python 3 (e.g. 'sudo apt install python3 python3-venv')."
  exit 1
fi

VENV_PATH="$SCRIPT_DIR/.venv"

if [[ -d "$VENV_PATH" && "$RECREATE" == true ]]; then
  WARN ".venv will be removed and recreated (--recreate)."
  rm -rf "$VENV_PATH"
fi

if [[ ! -d "$VENV_PATH" ]]; then
  INFO "Creating .venv ..."
  "$PY" -m venv "$VENV_PATH"
  OK ".venv created."
else
  INFO ".venv already exists. Reusing (use --recreate to rebuild)."
fi

VENV_PY="$VENV_PATH/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  ERR "Virtualenv python not found: $VENV_PY"
  exit 1
fi

INFO "Upgrading pip/setuptools/wheel ..."
"$VENV_PY" -m pip install --upgrade pip setuptools wheel
OK "Upgraded pip/setuptools/wheel."

REQ_FILE="$SCRIPT_DIR/requirements.txt"
if [[ -f "$REQ_FILE" ]]; then
  INFO "Installing requirements.txt ..."
  "$VENV_PY" -m pip install -r "$REQ_FILE"
  OK "Dependencies installed."
else
  WARN "requirements.txt not found. Skipping."
fi

INFO "Validating imports ..."
"$VENV_PY" - <<'PY'
import importlib, sys
mods = ['googleapiclient', 'google_auth_oauthlib']
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        missing.append(f"{m}: {e}")
if missing:
    print('MISSING:', '; '.join(missing))
    sys.exit(2)
print('IMPORTS_OK')
PY
OK "Import check passed."

if [[ ! -f "$SCRIPT_DIR/client_secret.json" ]]; then
  WARN "client_secret.json is missing. Follow README to download from Google Cloud Console and place it at project root."
else
  OK "client_secret.json found."
fi

echo
OK "Setup completed."
echo
echo -e "Next run command:" && echo "  $VENV_PATH/bin/python scripts/main.py"
echo -e "(Browser will open for Google auth on first run)"

if [[ "$RUN_AFTER" == true ]]; then
  INFO "Launching scripts/main.py (--run)."
  exec "$VENV_PY" "$SCRIPT_DIR/scripts/main.py"
fi
