# IBN ChatOps — Complete System

A full Intent-Based Networking automation system using your trained DistilBERT model.

## Folder Structure
```
ibn_chatops/
├── .env                       ← EDIT THIS FIRST (secrets)
├── .gitignore
├── config.py                  ← Loads from .env automatically
├── requirements.txt
├── start_all.sh               ← Linux/Mac: run all 3 services
├── start_all.bat              ← Windows: run all 3 services
├── core/
│   ├── engine.py              ← FastAPI core (brain of the system)
│   ├── model.py               ← IBN model loader + param extraction + CLI fill
│   ├── netmiko_push.py        ← SSH push to PNETLab devices
│   └── database.py            ← SQLite command history
├── bot/
│   └── telegram_bot.py        ← Telegram bot
├── dashboard/
│   ├── app.py                 ← Flask web dashboard (login protected)
│   └── templates/             ← HTML pages (includes login page)
└── models/
    └── ibn_dleberta/   ← PUT YOUR MODEL HERE
```

## Quick Setup

### Step 1 — Copy your model
Copy the `ibn_dleberta` folder into the `models/` folder.

### Step 2 — Edit .env
Open `.env` and set your values:
- `TELEGRAM_BOT_TOKEN` — from @BotFather on Telegram
- `TELEGRAM_ALERT_CHAT_ID` — optional; chat to notify on push failures / device down (see Alerts below)
- `DASHBOARD_PASSWORD` — your web dashboard password
- `DEVICE_USERNAME` / `DEVICE_PASSWORD` / `DEVICE_SECRET` — your PNETLab SSH credentials

### Step 3 — Set device IPs in config.py
Open `config.py` and update the `DEVICES` list with your PNETLab device IPs.

### Step 4 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 5 — Prepare PNETLab devices (SSH must be enabled)
On each Cisco device console:
```
username admin privilege 15 secret admin
crypto key generate rsa modulus 2048
ip ssh version 2
line vty 0 4
 transport input ssh
 login local
copy running-config startup-config
```

### Step 6 — Run
**Linux/Mac:**
```bash
bash start_all.sh
```

**Windows:**
```
Double-click start_all.bat
```

**Or manually (3 terminals):**
```bash
# Terminal 1 — start first, wait for "Model loaded ✅"
python -m uvicorn core.engine:app --host 127.0.0.1 --port 8000

# Terminal 2
python dashboard/app.py

# Terminal 3
python bot/telegram_bot.py
```

## Web Dashboard
Open http://localhost:5000 — login with your `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` from `.env`

Devices seeded from `config.py`'s `DEVICES` list on first run, and any
device added/edited/removed via **Manage Devices** in the dashboard, are
both usable end-to-end — the engine (push/show/status) and the dashboard
now read from the same device registry.

## API Docs
Open http://localhost:8000/docs

## Telegram Bot Commands
| Command | Description |
|---------|-------------|
| /start  | Welcome message |
| /device | Select target device |
| /status | Check all device status |
| /show   | Run a show command |
| /history| Recent commands |

Natural language examples:
- `create vlan 10 named Sales`
- `block host 10.1.1.5`
- `enable ospf process 1 area 0`
- `assign ip 192.168.1.1 255.255.255.0 to GigabitEthernet0/0`

## Preview & Confirm
The dashboard's Intent tab is now a two-step flow: **Preview CLI** classifies
the text and shows the generated CLI (editable) without touching any device;
**Confirm & Push** sends exactly that CLI through the same dangerous-command
guard as every other push path. "Execute directly" is still available for
quick one-shot/dry-run use, but preview-then-confirm is the safer default.

## Rollback
Every successful config push automatically snapshots the device's
running-config *immediately before* the change is applied (tagged
`auto:pre-change` in the backups table, linked to the command that
triggered it). The History page shows a **Rollback** button on any
successful, still-current push — it restores that exact pre-change
snapshot rather than trying to algebraically invert arbitrary Cisco CLI,
which isn't reliable in general.

## Config Diff
Every rollback-protected push (Safe Config Push / protected restore) now
also takes an `auto:post-change` snapshot once it succeeds, so the exact
delta the push made is available afterwards — the job page shows a
**"What Changed"** panel with a line-level diff (added/removed) as soon
as the job finishes. You can also compare any two historical backups of
the same device from the backup detail page's **Compare With Another
Backup** panel. Diffing is line-based (Python's `difflib`), not a
config-aware structural diff, but is enough to spot exactly what an
operator's change touched.

## Scheduled Backups
Set `SCHEDULED_BACKUP_INTERVAL_MINUTES` in `.env` (e.g. `60` for hourly)
to take a periodic "safety net" snapshot of every device, independent of
any push — tagged `scheduled` in the backups list, separate from the
`auto:pre-change`/`auto:post-change` snapshots taken around a push. Runs
in a background thread inside the engine process; leave at `0` (default)
to disable it. A failed scheduled backup (e.g. device unreachable) sends
a Telegram alert the same way a failed push does, and never blocks or
crashes the engine.

## Metrics History
The engine also samples CPU/memory/online status for every device on a
fixed interval (`METRICS_HISTORY_INTERVAL_SECONDS`, default 60s) and
keeps it for `METRICS_HISTORY_RETENTION_HOURS` (default 7 days),
independent of the Monitoring page's live polling. Click the small
graph icon on any device card on the **Monitoring** page for a CPU/memory
trend chart over the last hour / 6 hours / 24 hours / 7 days.

## Alerts
Set `TELEGRAM_ALERT_CHAT_ID` in `.env` to get a Telegram message whenever
a push fails or a device flips online/offline (see `core/notifier.py`).
Leave it unset to disable alerting entirely — it never blocks or fails a
request either way.

## Security notes
- Every device password/secret stored in the dashboard's device manager is
  encrypted at rest with Fernet (`ENCRYPTION_KEY` in `.env`). If you don't
  set one, a key is auto-generated into `.encryption_key` on first run —
  fine for local testing, but set it explicitly for anything beyond a lab
  so credentials survive a reinstall or a move to another host.
- User passwords are hashed with bcrypt.
- Dashboard forms are CSRF-protected (Flask-WTF); the `/login` route is
  rate-limited.
- Dangerous commands (`reload`, `write erase`, `debug ...`, etc.) are
  blocked on **every** push path — including the raw `/push` API and the
  dashboard's raw-CLI mode, not just the natural-language `/execute` path.
- Set `ENFORCE_SECURE_DEFAULTS=1` in `.env` for any deployment beyond your
  own lab — the app will then refuse to start if `SECRET_KEY`,
  `DASHBOARD_PASSWORD`, `DEVICE_PASSWORD`, `DEVICE_SECRET`, or
  `ENGINE_API_KEY` are still at their shipped default (unset, for the key).
- The engine's own API (port 8000) is now guarded by `ENGINE_API_KEY`: if
  set, every request except the bare health check on `/` must carry a
  matching `X-API-Key` header — the dashboard and bot send it
  automatically once it's configured in their own `.env`. Previously this
  API had **no** authentication at all, so anyone who could reach port
  8000 could push config directly, bypassing the dashboard's login
  entirely. Leave it empty only for a lab where port 8000 never leaves
  your own machine.

## Running the tests
```bash
pip install -r requirements.txt
pytest tests/ -v
```
The suite stubs out the ML model and Netmiko/paramiko network calls, so it
runs in a couple of seconds without a GPU, a trained model, or real
devices. It also documents two known extraction-accuracy edge cases as
`xfail` (see `tests/test_extract_params.py`) — natural language where the
regex slot-filler can pick the wrong value when multiple numbers/IPs
appear in an order that doesn't match the CLI template's expected order.

## Running with Docker
```bash
cp .env.example .env        # fill in your real values
# put your trained model in ./models/ibn_dleberta
docker compose up --build
```
This starts three containers — `engine` (port 8000), `dashboard` (port
5000), and `bot` — sharing a Docker volume for the SQLite DB. The
dashboard and bot reach the engine over the internal Docker network via
`API_URL=http://engine:8000` (set in `docker-compose.yml`), not
`127.0.0.1`.
