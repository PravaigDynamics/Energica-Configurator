#!/usr/bin/env bash
# Quick-start the Energica compositor service.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "ERROR: virtualenv not found. Run scripts/setup.sh first." >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$BACKEND_DIR/.venv/bin/activate"

PORT="${PORT:-8000}"
exec uvicorn compositor_service:app --host 0.0.0.0 --port "$PORT" --reload
