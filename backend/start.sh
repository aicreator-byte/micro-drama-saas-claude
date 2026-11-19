#!/usr/bin/env bash
# Start the Claude-leg backend from ANY working directory.
# (Future-dev 3b: .env is resolved relative to backend/, but this script
# also makes the CWD, venv and port explicit so a wrong CWD can never
# silently drop the key again.)
set -euo pipefail
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BACKEND_DIR"

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
exec python -m uvicorn app.main:app --host "$HOST" --port "$PORT"
