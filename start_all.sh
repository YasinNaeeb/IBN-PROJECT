#!/bin/bash
# ═══════════════════════════════════════════════════════
#  IBN ChatOps — Start all services (Linux / Mac)
# ═══════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  IBN ChatOps - Starting all services"
echo "============================================"

# Check Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  echo "❌ Python not found. Install Python 3.10+ first."
  exit 1
fi
PYTHON=$(command -v python3 || command -v python)

# Check .env exists
if [ ! -f ".env" ]; then
  echo "⚠️  .env file not found. Copy .env.example to .env and fill in your values."
  exit 1
fi

# Check token is set
if grep -q "YOUR_TELEGRAM_BOT_TOKEN" .env; then
  echo "⚠️  TELEGRAM_BOT_TOKEN is not set in .env"
  echo "   Get one from @BotFather on Telegram."
fi

# Resolve MODEL_PATH: use the value from .env if set, otherwise fall back
# to the same default config.py uses (models/ibn_dleberta).
MODEL_DIR=$(grep -E "^MODEL_PATH=" .env | head -1 | cut -d= -f2-)
MODEL_DIR=${MODEL_DIR:-models/ibn_dleberta}

# Check model exists
if [ ! -d "$MODEL_DIR" ]; then
  echo "❌ Model not found at $MODEL_DIR"
  echo "   Copy your trained model folder there first, or set MODEL_PATH in .env."
  exit 1
fi

echo ""
echo "[1/3] Starting Core Engine on port 8000..."
$PYTHON -m uvicorn core.engine:app --host 127.0.0.1 --port 8000 &
ENGINE_PID=$!
sleep 6

# Verify engine started
if ! kill -0 $ENGINE_PID 2>/dev/null; then
  echo "❌ Core Engine failed to start. Check the error above."
  exit 1
fi
echo "✅ Core Engine running (PID $ENGINE_PID)"

echo ""
echo "[2/3] Starting Web Dashboard on port 5000..."
$PYTHON dashboard/app.py &
DASH_PID=$!
sleep 2

if ! kill -0 $DASH_PID 2>/dev/null; then
  echo "❌ Dashboard failed to start."
  kill $ENGINE_PID 2>/dev/null
  exit 1
fi
echo "✅ Dashboard running (PID $DASH_PID)"

echo ""
echo "[3/3] Starting Telegram Bot..."
$PYTHON bot/telegram_bot.py &
BOT_PID=$!
sleep 2

if ! kill -0 $BOT_PID 2>/dev/null; then
  echo "❌ Telegram Bot failed to start. Check your TELEGRAM_BOT_TOKEN."
  kill $ENGINE_PID $DASH_PID 2>/dev/null
  exit 1
fi
echo "✅ Telegram Bot running (PID $BOT_PID)"

echo ""
echo "============================================"
echo "  All services started!"
echo "  Dashboard : http://localhost:5000"
echo "  API docs  : http://localhost:8000/docs"
echo "  Press Ctrl+C to stop all"
echo "============================================"

trap "echo ''; echo 'Stopping all services...'; kill $ENGINE_PID $DASH_PID $BOT_PID 2>/dev/null; echo 'Done.'" INT TERM
wait
