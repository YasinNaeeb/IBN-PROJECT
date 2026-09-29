# ═══════════════════════════════════════════════════════════
#  IBN ChatOps — Configuration
#  IBN Lab — 3 Routers + 3 Switches
# ═══════════════════════════════════════════════════════════
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

# Load .env
_env_path = BASE_DIR / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# ── Telegram ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

_allowed_raw = os.environ.get("TELEGRAM_ALLOWED_USERS", "").strip()
TELEGRAM_ALLOWED_USERS = {
    int(uid.strip()) for uid in _allowed_raw.split(",") if uid.strip().isdigit()
} if _allowed_raw else set()

DASHBOARD_PUBLIC_URL = os.environ.get("DASHBOARD_PUBLIC_URL", "").strip()

# Chat/group/user ID the bot posts operational alerts to (push failures,
# device online/offline transitions). Leave empty to disable alerting —
# see core/notifier.py.
TELEGRAM_ALERT_CHAT_ID = os.environ.get("TELEGRAM_ALERT_CHAT_ID", "").strip()

# ── Model ─────────────────────────────────────────────────
# NOTE: this fallback name must match README.md, docker-compose.yml,
# install.bat and models/PUT_MODEL_HERE.txt (all say "ibn_dleberta").
# It's only used if MODEL_PATH isn't set in .env.
_default_model_path = str(BASE_DIR / "models" / "ibn_dleberta")
MODEL_PATH = os.environ.get("MODEL_PATH", _default_model_path)

CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.50"))

# ── FastAPI ───────────────────────────────────────────────
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8000"))
API_URL  = os.environ.get("API_URL", f"http://{API_HOST}:{API_PORT}")

# ── Dashboard ─────────────────────────────────────────────
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000
SECRET_KEY     = os.environ.get("SECRET_KEY", "ibn_chatops_secret_change_me")
DASHBOARD_USERNAME = os.environ.get("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")

# ── IBN Lab Devices ───────────────────────────────────────
# To add a new device: add an entry here, then add its links in TOPOLOGY_LINKS below.
# PNetLab server IP: 192.168.64.133  ← reserved, do NOT use

_u = os.environ.get("DEVICE_USERNAME", "admin")
_p = os.environ.get("DEVICE_PASSWORD", "admin")
_s = os.environ.get("DEVICE_SECRET",   "admin")

DEVICES = [
    # ── Routers ───────────────────────────────────────────
    {"name": "R1",  "host": "192.168.64.101", "username": _u, "password": _p, "secret": _s, "device_type": "cisco_ios", "conn_timeout": 30},
    {"name": "R2",  "host": "192.168.64.102", "username": _u, "password": _p, "secret": _s, "device_type": "cisco_ios", "conn_timeout": 30},
    {"name": "R3",  "host": "192.168.64.103", "username": _u, "password": _p, "secret": _s, "device_type": "cisco_ios", "conn_timeout": 30},
    # ── Switches ──────────────────────────────────────────
    {"name": "SW3", "host": "192.168.64.113", "username": _u, "password": _p, "secret": _s, "device_type": "cisco_ios", "conn_timeout": 30},
    {"name": "SW4", "host": "192.168.64.114", "username": _u, "password": _p, "secret": _s, "device_type": "cisco_ios", "conn_timeout": 30},
    {"name": "SW5", "host": "192.168.64.115", "username": _u, "password": _p, "secret": _s, "device_type": "cisco_ios", "conn_timeout": 30},
    # ── Add new devices here ──────────────────────────────
    # {"name": "R4",  "host": "192.168.64.104", "username": _u, "password": _p, "secret": _s, "device_type": "cisco_ios", "conn_timeout": 30},
]

# ── Topology Links ────────────────────────────────────────
# Defines how devices are connected for the graphical topology view.
# Each entry: {"from": "DEVICE_NAME", "to": "DEVICE_NAME", "subnet": "x.x.x.x/xx"}
# Use "cloud" as a special name for the pnet0 internet/cloud node.
#
# ✅ To add a new router or switch:
#   1. Add it to DEVICES above
#   2. Add its link(s) here
#   Example:
#     {"from": "R1", "to": "R4",  "subnet": "10.1.16.0/30"},
#     {"from": "R4", "to": "SW6", "subnet": "10.4.16.0/30"},
#
# The topology page will automatically redraw with the new device.

TOPOLOGY_LINKS = [
    {"from": "cloud", "to": "R1",  "subnet": "192.168.64.0/24"},
    {"from": "R1",    "to": "R2",  "subnet": "10.1.12.0/30"},
    {"from": "R1",    "to": "R3",  "subnet": "10.1.13.0/30"},
    {"from": "R1",    "to": "SW4", "subnet": "10.1.14.0/30"},
    {"from": "R2",    "to": "SW3", "subnet": "10.2.13.0/30"},
    {"from": "R3",    "to": "SW5", "subnet": "10.3.15.0/30"},
    # {"from": "R1",    "to": "R4",  "subnet": "10.1.16.0/30"},
    # {"from": "R4",    "to": "SW6", "subnet": "10.4.16.0/30"},
]

# ── Database ──────────────────────────────────────────────
_default_db_path = str(BASE_DIR / "ibn_chatops.db")
DB_PATH = os.environ.get("DB_PATH", _default_db_path)

# ── Engine API authentication ─────────────────────────────
# Shared secret the dashboard/bot send as the X-API-Key header on every
# request to the engine (port 8000). Without this, anyone who can reach
# the engine's port can push config directly, bypassing the dashboard's
# login entirely — so this closes that gap.
# Leave empty ONLY for local lab testing where the engine port isn't
# exposed beyond your own machine; an empty key means the engine accepts
# unauthenticated requests. Generate one with:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
ENGINE_API_KEY = os.environ.get("ENGINE_API_KEY", "").strip()

# ── Scheduled (periodic) config backups ───────────────────
# Minutes between automatic "safety net" backups of every device, taken
# independently of any push (tagged 'scheduled' in config_backups, vs.
# 'auto:pre-change' for the ones taken right before a push). 0 disables
# the scheduler entirely.
SCHEDULED_BACKUP_INTERVAL_MINUTES = int(os.environ.get("SCHEDULED_BACKUP_INTERVAL_MINUTES", "0") or "0")

# ── Metrics history sampling ───────────────────────────────
# How often (seconds) to persist a CPU/memory/online sample per device
# for the Monitoring page's history graphs, and how long to keep samples.
METRICS_HISTORY_INTERVAL_SECONDS = int(os.environ.get("METRICS_HISTORY_INTERVAL_SECONDS", "60") or "60")
METRICS_HISTORY_RETENTION_HOURS  = int(os.environ.get("METRICS_HISTORY_RETENTION_HOURS", "168") or "168")

# ── Config backups (filesystem) ──────────────────────────
# Every backup is stored both as a row in config_backups (for fast lookup
# and the dashboard/API) AND as a plain-text file here (for out-of-band
# recovery — e.g. a DBA restoring from disk if the DB itself is lost).
BACKUP_DIR = os.environ.get("BACKUP_DIR", str(BASE_DIR / "backups"))
os.makedirs(BACKUP_DIR, exist_ok=True)

# ── Security ──────────────────────────────────────────────
# Set ENFORCE_SECURE_DEFAULTS=1 in .env for any non-lab / non-local deployment.
# When set, the dashboard refuses to start if it detects unchanged default
# secrets (SECRET_KEY, DASHBOARD_PASSWORD, DEVICE_PASSWORD/SECRET).
ENFORCE_SECURE_DEFAULTS = os.environ.get("ENFORCE_SECURE_DEFAULTS", "0") == "1"

_INSECURE_DEFAULTS = {
    "SECRET_KEY":          "ibn_chatops_secret_change_me",
    "DASHBOARD_PASSWORD":  "admin123",
    "DEVICE_PASSWORD":     "admin",
    "DEVICE_SECRET":       "admin",
    # No shipped default for this one — an empty value just means
    # "engine API auth is off", which is the thing we want to flag.
    "ENGINE_API_KEY":      "",
}


def check_insecure_defaults() -> list[str]:
    """Return the names of any secrets still set to their shipped default value
    (or, for ENGINE_API_KEY, still unset)."""
    current = {
        "SECRET_KEY":         SECRET_KEY,
        "DASHBOARD_PASSWORD": DASHBOARD_PASSWORD,
        "DEVICE_PASSWORD":    _p,
        "DEVICE_SECRET":      _s,
        "ENGINE_API_KEY":     ENGINE_API_KEY,
    }
    return [name for name, default in _INSECURE_DEFAULTS.items() if current[name] == default]


# Fernet key used to encrypt device passwords/secrets at rest in the DB.
# Falls back to a locally-generated, gitignored key file so the app still
# works out of the box — but for real deployments set ENCRYPTION_KEY in .env
# so credentials survive across machines/restores and aren't tied to one host.
_key_env = os.environ.get("ENCRYPTION_KEY", "").strip()
if _key_env:
    ENCRYPTION_KEY = _key_env.encode()
else:
    from cryptography.fernet import Fernet
    _key_path = BASE_DIR / ".encryption_key"
    if _key_path.exists():
        ENCRYPTION_KEY = _key_path.read_bytes().strip()
    else:
        ENCRYPTION_KEY = Fernet.generate_key()
        _key_path.write_bytes(ENCRYPTION_KEY)
        print(
            "⚠️  No ENCRYPTION_KEY set in .env — generated one at "
            f"{_key_path}. Set ENCRYPTION_KEY explicitly for production "
            "so stored device credentials remain decryptable after a "
            "reinstall or move to another host."
        )

# CLI patterns that must never be pushed, even via the raw /push endpoint
# (previously only the classify/execute path enforced this — the raw push
# path bypassed it entirely).
DANGEROUS_CLI_PATTERNS = [
    # 'reload' and 'debug ' were removed on request so reload_device /
    # debug_commands can actually push. reload is still handled as a
    # special interactive case in netmiko_push.py (confirm prompts +
    # expected session drop on reboot) — that handling is what makes it
    # safe to run, not this list, so don't rely on this list alone.
    r"^\s*write\s+erase\b",
    r"^\s*erase\s+",
    r"^\s*format\s+",
    r"^\s*delete\s+/force",
    r"^\s*no\s+enable\s+password",
]
