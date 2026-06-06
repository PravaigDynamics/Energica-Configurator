#!/usr/bin/env bash
# Energica Configurator — One-command project setup
# Usage: bash scripts/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> Energica Configurator Setup"
echo "    Root: $ROOT_DIR"
echo ""

# -----------------------------------------------------------------------
# Backend
# -----------------------------------------------------------------------
echo "[1/4] Installing Python dependencies..."
cd "$ROOT_DIR/backend"

if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install Python 3.10+ and retry." >&2
  exit 1
fi

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "      Python deps installed."

# Copy .env if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "      .env created from .env.example — edit before starting."
fi

# -----------------------------------------------------------------------
# Frontend
# -----------------------------------------------------------------------
echo "[2/4] Installing Node.js dependencies..."
cd "$ROOT_DIR/frontend"

if ! command -v node &>/dev/null; then
  echo "ERROR: node not found. Install Node.js 18+ and retry." >&2
  exit 1
fi

npm install --silent
echo "      Node deps installed."

# Create .env.local if not present
if [ ! -f .env.local ]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
  echo "      .env.local created."
fi

# -----------------------------------------------------------------------
# Layer directories
# -----------------------------------------------------------------------
echo "[3/4] Creating layer directories..."
for model in eva essesse9 ego ribelle; do
  mkdir -p "$ROOT_DIR/backend/layers/$model"
done
echo "      Layer directories ready."

# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------
echo ""
echo "[4/4] Setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env (set LAYER_PATH, REDIS_URL if needed)"
echo "  2. Extract PSD layers:"
echo "       cd backend && source .venv/bin/activate"
echo "       python extract_psd.py /path/to/EVA.psd --model eva"
echo "       python extract_psd.py /path/to/ESSESSE9.psd --model essesse9"
echo "       python extract_psd.py /path/to/EGO.psd --model ego"
echo "       python extract_psd.py /path/to/RIBELLE.psd --model ribelle"
echo "  3. Start backend:"
echo "       cd backend && source .venv/bin/activate"
echo "       uvicorn compositor_service:app --reload --port 8000"
echo "  4. Start frontend (new terminal):"
echo "       cd frontend && npm run dev"
echo "  5. Open: http://localhost:3000/test"
