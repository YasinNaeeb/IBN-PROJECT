@echo off
REM ═══════════════════════════════════════════════════════
REM  IBN ChatOps — Start all services (Windows)
REM ═══════════════════════════════════════════════════════
cd /d "%~dp0"

echo ============================================
echo   IBN ChatOps - Starting all services
echo ============================================

REM Check Python is available
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found on PATH. Install Python 3.10+ first.
    pause
    exit /b 1
)

REM Check .env exists
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo Copy .env and fill in your values.
    pause
    exit /b 1
)

REM Resolve MODEL_PATH: use the value from .env if set, otherwise
REM fall back to the same default config.py uses (models\ibn_dleberta).
set "MODEL_DIR=models\ibn_dleberta"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="MODEL_PATH" if not "%%B"=="" set "MODEL_DIR=%%B"
)

REM Check model
if not exist "%MODEL_DIR%" (
    echo [ERROR] Model not found at %MODEL_DIR%
    echo Copy your trained model folder there first, or set MODEL_PATH in .env.
    pause
    exit /b 1
)

echo.
echo [1/3] Starting Core Engine on port 8000...
start "IBN-Engine" cmd /k "python -m uvicorn core.engine:app --host 127.0.0.1 --port 8000"
timeout /t 7 /nobreak >nul

echo [2/3] Starting Web Dashboard on port 5000...
start "IBN-Dashboard" cmd /k "python dashboard\app.py"
timeout /t 3 /nobreak >nul

echo [3/3] Starting Telegram Bot...
start "IBN-Bot" cmd /k "python bot\telegram_bot.py"
timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo   All services started!
echo   Dashboard : http://localhost:5000
echo   API docs  : http://localhost:8000/docs
echo   Close the three windows to stop services
echo ============================================
pause
