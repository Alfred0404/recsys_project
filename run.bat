@echo off
rem Windows: set up what is missing, then serve the site on http://127.0.0.1:8000
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Creating the Python environment...
  python -m venv .venv || goto :fail
)
set PY=.venv\Scripts\python.exe

echo Installing dependencies...
%PY% -m pip install -q -r requirements.txt || goto :fail
%PY% -m src.data.download || goto :fail
if not exist dataset\processed\close_prices.parquet (
  %PY% -m src.data.load_and_check || goto :fail
)
if not exist dataset\experiment\model.npz (
  echo Training the model, about 2 minutes...
  %PY% -m src.train.run --skip-ablation || goto :fail
)

rem Open the browser once the server has had time to start.
start "" /b cmd /c "timeout /t 5 /nobreak >nul & start http://127.0.0.1:8000"
echo Spread is running on http://127.0.0.1:8000 (Ctrl+C to stop)
%PY% -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
goto :eof

:fail
echo.
echo Setup failed: see the message above. Python 3.11 or newer must be installed and on the PATH.
pause
exit /b 1
