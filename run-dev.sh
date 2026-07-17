#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

if [[ -f "$PROJECT_DIR/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

WALLET_PORT="${WALLET_PORT:-8000}"
THIRD_PARTY_PORT="${THIRD_PARTY_PORT:-8010}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.11 is required for Django 3.2. Install it or set PYTHON_BIN to a compatible interpreter." >&2
  exit 1
fi

if [[ -x "$VENV_DIR/bin/python" ]] && ! "$VENV_DIR/bin/python" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 11))'; then
  echo "Existing .venv does not use Python 3.11. Remove it and rerun this script." >&2
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install -q -r "$PROJECT_DIR/wallet/requirements.txt" -r "$PROJECT_DIR/third-party/requirements.txt"
"$VENV_DIR/bin/python" "$PROJECT_DIR/wallet/manage.py" migrate --noinput

cleanup() {
  kill "$wallet_pid" "$third_party_pid" 2>/dev/null || true
  wait "$wallet_pid" "$third_party_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
  cd "$PROJECT_DIR/wallet"
  exec "$VENV_DIR/bin/python" manage.py runserver "0.0.0.0:$WALLET_PORT"
) &
wallet_pid=$!

(
  cd "$PROJECT_DIR/third-party"
  exec "$VENV_DIR/bin/python" app.py
) &
third_party_pid=$!

echo "Wallet: http://localhost:$WALLET_PORT"
echo "Third-party: http://localhost:$THIRD_PARTY_PORT"
wait "$wallet_pid" "$third_party_pid"
