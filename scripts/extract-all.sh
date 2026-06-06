#!/usr/bin/env bash
# Energica Configurator — Batch PSD extraction
#
# Usage:
#   bash scripts/extract-all.sh \
#     /path/to/EVA.psd \
#     /path/to/ESSESSE9.psd \
#     /path/to/EGO.psd \
#     /path/to/RIBELLE.psd

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND="$ROOT_DIR/backend"

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <eva.psd> <essesse9.psd> <ego.psd> <ribelle.psd>"
  exit 1
fi

EVA_PSD="$1"
ESSESSE9_PSD="$2"
EGO_PSD="$3"
RIBELLE_PSD="$4"

cd "$BACKEND"

if [ ! -d .venv ]; then
  echo "ERROR: virtualenv not found. Run scripts/setup.sh first." >&2
  exit 1
fi

# shellcheck source=/dev/null
source .venv/bin/activate

declare -A MODELS=(
  ["eva"]="$EVA_PSD"
  ["essesse9"]="$ESSESSE9_PSD"
  ["ego"]="$EGO_PSD"
  ["ribelle"]="$RIBELLE_PSD"
)

for model in eva essesse9 ego ribelle; do
  psd="${MODELS[$model]}"
  echo ""
  echo "==> Extracting model: $model"
  echo "    PSD: $psd"
  python extract_psd.py "$psd" --model "$model" --output ./layers
done

echo ""
echo "==> All models extracted."
echo "    Start backend: uvicorn compositor_service:app --reload --port 8000"
