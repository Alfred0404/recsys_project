#!/usr/bin/env bash
# macOS / Linux: install everything (venv, dependencies, data, trained model) without starting the server.
# Start it afterwards with ./run.sh (instant once installed).
set -euo pipefail
cd "$(dirname "$0")"

PYBIN="${PYTHON:-python3}"
if ! command -v "$PYBIN" >/dev/null 2>&1; then
  echo "Python not found. Install Python 3.11 or newer first." >&2; exit 1
fi
if ! "$PYBIN" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
  echo "Python 3.11 or newer is required (found: $("$PYBIN" --version))." >&2; exit 1
fi

START=$(date +%s)

if [ ! -x .venv/bin/python ]; then
  echo "[1/4] Creating the Python environment..."
  "$PYBIN" -m venv .venv
fi
PY=.venv/bin/python

# uv is much faster than pip when available; pip works everywhere.
if command -v uv >/dev/null 2>&1; then
  PIP=(uv pip install -q --python "$PY")
else
  "$PY" -m pip install -q --upgrade pip
  PIP=("$PY" -m pip install -q --disable-pip-version-check)
fi

echo "[2/4] Installing dependencies..."
# On Linux, the default torch wheel bundles CUDA (~2.5 GB). The CPU wheel is enough here.
if [ "$(uname -s)" = "Linux" ] && ! "$PY" -c "import torch" 2>/dev/null; then
  "${PIP[@]}" "torch>=2.2,<3" --index-url https://download.pytorch.org/whl/cpu
fi
"${PIP[@]}" -r requirements.txt

# If the zip ships the trained weights (dataset/experiment) and the prepared prices
# (dataset/processed), nothing is downloaded and nothing is retrained.
if [ -f dataset/experiment/model.npz ] && [ -d dataset/experiment/finance ] \
   && [ -f dataset/processed/close_prices.parquet ]; then
  echo "[3/4] Prepared data found, skipping download."
  echo "[4/4] Trained model found, keeping the existing weights (no retraining)."
else
  echo "[3/4] Downloading and preparing the data..."
  "$PY" -m src.data.download
  [ -f dataset/processed/close_prices.parquet ] || "$PY" -m src.data.load_and_check
  if [ ! -f dataset/experiment/model.npz ]; then
    echo "[4/4] Training the model, about 2 minutes..."
    "$PY" -m src.train.run --skip-ablation
  else
    echo "[4/4] Trained model found, keeping the existing weights (no retraining)."
  fi
fi

echo "Done in $(( $(date +%s) - START )) s. Start the site with ./run.sh"
