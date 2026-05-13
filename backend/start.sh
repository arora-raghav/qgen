#!/usr/bin/env bash
# start.sh — start the QGen backend in local dev mode
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create virtualenv if missing
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install / upgrade deps
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
  echo "Creating .env from .env.example — please set OPENAI_API_KEY in backend/.env"
  cp .env.example .env
fi

export $(grep -v '^#' .env | xargs -d '\n') 2>/dev/null || true

echo "Starting QGen backend on http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
