@echo off
rem Windows: install everything (venv, dependencies, data, trained model) without starting the server.
rem Start it afterwards with run.bat (instant once installed).
setlocal
cd /d "%~dp0"

set BASEPY=python
where py >nul 2>nul && set BASEPY=py -3
%BASEPY% -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or newer is required and must be on the PATH.
  goto :fail
)

if not exist .venv\Scripts\python.exe (
  echo [1/4] Creating the Python environment...
  %BASEPY% -m venv .venv || goto :fail
)
set PY=.venv\Scripts\python.exe

echo [2/4] Installing dependencies...
where uv >nul 2>nul
if not errorlevel 1 (
  uv pip install -q --python %PY% -r requirements.txt || goto :fail
) else (
  %PY% -m pip install -q --disable-pip-version-check -r requirements.txt || goto :fail
)

rem If the zip ships the trained weights (dataset\experiment) and the prepared prices
rem (dataset\processed), nothing is downloaded and nothing is retrained.
if exist dataset\experiment\model.npz if exist dataset\experiment\finance if exist dataset\processed\close_prices.parquet (
  echo [3/4] Prepared data found, skipping download.
  echo [4/4] Trained model found, keeping the existing weights, no retraining.
  goto :done
)

echo [3/4] Downloading and preparing the data...
%PY% -m src.data.download || goto :fail
if not exist dataset\processed\close_prices.parquet (
  %PY% -m src.data.load_and_check || goto :fail
)

if not exist dataset\experiment\model.npz (
  echo [4/4] Training the model, about 2 minutes...
  %PY% -m src.train.run --skip-ablation || goto :fail
) else (
  echo [4/4] Trained model found, keeping the existing weights, no retraining.
)

:done

echo.
echo Done. Start the site with run.bat
pause
exit /b 0

:fail
echo.
echo Setup failed: see the message above.
pause
exit /b 1
