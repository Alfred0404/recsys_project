#!/usr/bin/env bash
# macOS / Linux: set up what is missing, then serve the site on http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "Creating the Python environment..."
  "${PYTHON:-python3}" -m venv .venv
fi
PY=.venv/bin/python

echo "Installing dependencies..."
"$PY" -m pip install -q -r requirements.txt
"$PY" -m src.data.download
[ -f dataset/processed/close_prices.parquet ] || "$PY" -m src.data.load_and_check
if [ ! -f dataset/experiment/model.npz ]; then
  echo "Training the model, about 2 minutes..."
  "$PY" -m src.train.run
fi

# Open the browser once the server has had time to start.
( sleep 5; open http://127.0.0.1:8000 2>/dev/null || xdg-open http://127.0.0.1:8000 2>/dev/null || true ) &
echo "Spread is running on http://127.0.0.1:8000 (Ctrl+C to stop)"
exec "$PY" -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
