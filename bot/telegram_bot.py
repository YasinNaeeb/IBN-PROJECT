"""
IBN ChatOps — Telegram Bot
Run: python bot/telegram_bot.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
import logging
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from config import (TELEGRAM_BOT_TOKEN, API_URL, DEVICES,
                    TELEGRAM_ALLOWED_USERS, DASHBOARD_PUBLIC_URL, ENGINE_API_KEY)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Track which device each user selected
user_device_map: dict[int, str] = {}

# Intents that should be auto-run as show/exec commands
SHOW_INTENTS = {
    "ping_test", "traceroute",
    "show_cdp_lldp", "show_interfaces", "show_ip_brief",
    "show_mac_arp", "show_routes", "show_running_config",
    "show_spanning_tree", "show_version", "show_vlan",
    "vlan_show", "dhcp_show",
    "troubleshoot_connectivity", "troubleshoot_dhcp", "troubleshoot_vlan",
}

# CLI commands for show intents
SHOW_CLI = {
    "ping_test":               "ping {ip} repeat 5",
    "traceroute":              "traceroute {ip}",
    "show_cdp_lldp":          "show cdp neighbors detail",
    "show_interfaces":        "show interfaces",
    "show_ip_brief":          "show ip interface brief",
    "show_mac_arp":           "show arp",
    "show_routes":            "show ip route",
    "show_running_config":    "show running-config",
    "show_spanning_tree":     "show spanning-tree",
    "show_version":           "show version",
    "show_vlan":              "show vlan brief",
    "vlan_show":              "show vlan brief",
    "dhcp_show":              "show ip dhcp binding",
    "troubleshoot_connectivity": "show ip interface brief",
    "troubleshoot_dhcp":      "show ip dhcp binding",
    "troubleshoot_vlan":      "show vlan brief",
}


# ── Helpers ───────────────────────────────────────────────────────────

def api(endpoint: str, payload: dict = None, method="POST") -> dict:
    url = f"{API_URL}/{endpoint}"
    try:
        # A push can run several exec/config commands back-to-back on the
        # device (each with its own ~20-30s read_timeout inside netmiko),
        # so the engine can legitimately take longer than 30s to respond.
        # A short client-side timeout here just turns a slow-but-successful
        # push into a false "Read timed out" error in Telegram while the
        # engine keeps working in the background. 90s comfortably covers a
        # multi-command push while still failing fast on a truly dead engine.
        if method == "GET":
            r = requests.get(url, timeout=90)
        else:
            r = requests.post(url, json=payload, timeout=90)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def device_keyboard():
    buttons = [[InlineKeyboardButton(d["name"], callback_data=f"dev:{d['name']}")] for d in DEVICES]
    return InlineKeyboardMarkup(buttons)


def dashboard_button():
    """Inline button that opens the dashboard. Uses a real Telegram Mini App
    (in-chat WebView) if DASHBOARD_PUBLIC_URL is https, otherwise falls back
    to a plain link button that opens in the external browser. Returns None
    if no URL is configured at all."""
    if not DASHBOARD_PUBLIC_URL:
        return None
    if DASHBOARD_PUBLIC_URL.startswith("https://"):
        btn = InlineKeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=DASHBOARD_PUBLIC_URL))
    else:
        btn = InlineKeyboardButton("📊 Open Dashboard (browser)", url=DASHBOARD_PUBLIC_URL)
    return InlineKeyboardMarkup([[btn]])


# ── Access control ────────────────────────────────────────────────────

def is_authorized(user_id: int | None) -> bool:
    """If TELEGRAM_ALLOWED_USERS is empty, the bot is open to everyone
    (useful for local testing). Set it in .env to lock the bot down —
    important once it's able to push config to real devices."""
    if not TELEGRAM_ALLOWED_USERS:
        return True
    return user_id in TELEGRAM_ALLOWED_USERS


async def _deny(update: Update):
    msg = "🚫 You're not authorized to use this bot. Contact the administrator to be added."
    if update.callback_query:
        await update.callback_query.answer(msg, show_alert=True)
    elif update.effective_message:
        await update.effective_message.reply_text(msg)


def require_auth(func):
    """Decorator for handlers — blocks unauthorized users before the
    handler body runs, and logs the attempt."""
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not is_authorized(user.id if user else None):
            log.warning(
                "Unauthorized access attempt: user_id=%s username=%s",
                user.id if user else "unknown",
                user.username if user else "unknown",
            )
            await _deny(update)
            return
        return await func(update, ctx)
    return wrapper


def confidence_bar(conf: float) -> str:
    filled = int(conf * 10)
    return "█" * filled + "░" * (10 - filled) + f" {conf*100:.1f}%"


def extract_ip(text: str) -> str:
    """Extract IP from user text."""
    import re
    m = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', text)
    return m.group(1) if m else None


def get_show_command(intent: str, text: str) -> str:
    """Get the show command for a given intent."""
    cmd = SHOW_CLI.get(intent, "show version")
    ip = extract_ip(text)
    if ip:
        cmd = cmd.replace("{ip}", ip)
    else:
        cmd = cmd.replace("{ip}", "127.0.0.1")
    return cmd


# ── Command handlers ──────────────────────────────────────────────────

@require_auth
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Welcome to IBN ChatOps, {name}!\n\n"
        "I turn plain English into Cisco CLI and push it to your virtual devices.\n\n"
        "Commands:\n"
        "  /device — select a target device\n"
        "  /status — check all device status\n"
        "  /show   — run a show command\n"
        "  /history — recent commands\n"
        "  /dashboard — open the web dashboard\n"
        "  /help   — show this message\n\n"
        "Just type your intent to get started:\n"
        "_e.g._ `create vlan 10 named Sales`\n"
        "_e.g._ `ping 192.168.1.1`\n"
        "_e.g._ `show interfaces`",
        parse_mode="Markdown",
        reply_markup=dashboard_button()
    )


@require_auth
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, ctx)


@require_auth
async def cmd_device(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Select a target device:",
        reply_markup=device_keyboard()
    )


@require_auth
async def cmd_dashboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = dashboard_button()
    if not kb:
        await update.message.reply_text(
            "Dashboard link isn't configured yet.\n\n"
            "Set `DASHBOARD_PUBLIC_URL` in your `.env` to a public HTTPS URL "
            "(e.g. an ngrok tunnel or your server's real domain) to enable this button.",
            parse_mode="Markdown"
        )
        return
    await update.message.reply_text("Tap below to open the dashboard:", reply_markup=kb)


@require_auth
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Checking device status...")
    result = api("devices/status", method="GET")
    if "error" in result:
        await update.message.reply_text(f"❌ Error: {result['error']}")
        return

    lines = ["*Device Status*\n"]
    for d in result.get("devices", []):
        icon = "🟢" if d["online"] else "🔴"
        lines.append(f"{icon} *{d['name']}* — {'Online' if d['online'] else 'Offline'}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_auth
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = api("history?limit=5", method="GET")
    if "error" in result:
        await update.message.reply_text(f"❌ {result['error']}")
        return

    cmds = result.get("commands", [])
    if not cmds:
        await update.message.reply_text("No commands yet.")
        return

    lines = ["*Last 5 commands:*\n"]
    for c in cmds:
        icon = "✅" if c["status"] == "success" else ("🔄" if c["status"] == "pending" else "❌")
        lines.append(f"{icon} `{c['input_text'][:40]}` → _{c['intent']}_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_auth
async def cmd_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    device  = user_device_map.get(user_id)
    if not device:
        await update.message.reply_text(
            "Please select a device first with /device"
        )
        return

    if not ctx.args:
        await update.message.reply_text(
            "Usage: `/show show ip interface brief`\nor `/show show vlan brief`",
            parse_mode="Markdown"
        )
        return

    command = " ".join(ctx.args)
    await update.message.reply_text(f"⏳ Running on {device}...")
    result = api("show", {"device": device, "command": command})

    if result.get("success"):
        output = result["output"] or "(no output)"
        if len(output) > 3800:
            output = output[:3800] + "\n...(truncated)"
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ {result.get('error', 'Unknown error')}")


# ── Callback handler ──────────────────────────────────────────────────

@require_auth
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    user_id = query.from_user.id

    if data.startswith("dev:"):
        device = data[4:]
        user_device_map[user_id] = device
        await query.edit_message_text(
            f"✅ Target device set to *{device}*\n\nNow type your intent!",
            parse_mode="Markdown"
        )

    elif data.startswith("exec:"):
        import base64
        _, device, cli_b64 = data.split(":", 2)
        cli  = base64.b64decode(cli_b64.encode()).decode()
        user = query.from_user.username or query.from_user.first_name

        await query.edit_message_text(f"⏳ Pushing to {device}...")
        # Push CLI directly via /push endpoint (bypasses re-classification)
        result = api("push", {
            "cli":    cli,
            "device": device,
            "source": "telegram",
            "user":   user,
        })
        if result.get("pushed"):
            output = result.get("output") or "Done"
            if len(output) > 3500:
                output = output[:3500] + "...(truncated)"
            await query.edit_message_text(
                f"✅ *Pushed to {device}*\n\n```\n{output}\n```",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ Failed: {result.get('error') or result.get('reason', 'unknown')}",
                parse_mode="Markdown"
            )

    elif data.startswith("show:"):
        # show:<device>:<command_b64>
        import base64
        _, device, cmd_b64 = data.split(":", 2)
        command = base64.b64decode(cmd_b64.encode()).decode()

        await query.edit_message_text(f"⏳ Running on {device}...")
        result = api("show", {"device": device, "command": command})

        if result.get("success"):
            output = result["output"] or "(no output)"
            if len(output) > 3500:
                output = output[:3500] + "\n...(truncated)"
            await query.edit_message_text(
                f"✅ *Output from {device}*\n\n```\n{output}\n```",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ Failed: {result.get('error', 'Unknown error')}",
                parse_mode="Markdown"
            )

    elif data == "change_dev":
        await query.edit_message_text(
            "Select a new target device:",
            reply_markup=device_keyboard()
        )

    elif data == "cancel":
        await query.edit_message_text("❌ Cancelled.")


# ── Main message handler ──────────────────────────────────────────────

@require_auth
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    import base64
    user_id  = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    text     = update.message.text.strip()

    # Classify intent
    result = api("classify", {"text": text, "source": "telegram", "user": username})

    if "error" in result:
        await update.message.reply_text(
            f"❌ Engine error: {result['error']}\n\nMake sure the core engine is running."
        )
        return

    intent = result.get("intent", "unknown")
    conf   = result.get("confidence", 0)
    cli    = result.get("cli")
    bar    = confidence_bar(conf)
    device = user_device_map.get(user_id)

    # ── Handle show/diagnostic intents automatically ──────────────────
    if intent in SHOW_INTENTS:
        show_cmd = get_show_command(intent, text)

        if not device:
            # Ask user to select device first
            buttons = [[InlineKeyboardButton(d["name"], callback_data=f"dev:{d['name']}")] for d in DEVICES]
            await update.message.reply_text(
                f"🔍 *Intent detected:* `{intent}`\n"
                f"📊 Confidence: {bar}\n\n"
                f"*Command to run:*\n```\n{show_cmd}\n```\n\n"
                "Select a device to run on:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return

        # Device selected — run it automatically
        cmd_b64 = base64.b64encode(show_cmd.encode()).decode()
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"▶️ Run on {device}", callback_data=f"show:{device}:{cmd_b64}"),
                InlineKeyboardButton("🔄 Change device", callback_data="change_dev"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
            ]
        ])
        await update.message.reply_text(
            f"🔍 *Intent:* `{intent}`\n"
            f"📊 Confidence: {bar}\n"
            f"🖥️ Device: *{device}*\n\n"
            f"*Command to run:*\n```\n{show_cmd}\n```",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return

    # ── Handle truly out of scope ─────────────────────────────────────
    if intent == "out_of_scope" or not result.get("actionable"):
        await update.message.reply_text(
            f"🤔 I couldn't map that to a network command.\n\n"
            f"Intent: `{intent}`\n"
            f"Confidence: {bar}\n\n"
            "Try rephrasing, e.g.:\n"
            "`create vlan 10 named Sales`\n"
            "`ping 192.168.1.1`\n"
            "`show interfaces`\n"
            "`block host 10.1.1.5`",
            parse_mode="Markdown"
        )
        return

    # ── Handle config intents ─────────────────────────────────────────
    if not device:
        buttons = [[InlineKeyboardButton(d["name"], callback_data=f"dev:{d['name']}")] for d in DEVICES]
        await update.message.reply_text(
            f"✅ *Intent detected:* `{intent}`\n"
            f"📊 Confidence: {bar}\n\n"
            f"*CLI preview:*\n```\n{cli}\n```\n\n"
            "Select a device to push to:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Device selected — show confirm / cancel
    cli_b64 = base64.b64encode(cli.encode()).decode()
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Push to " + device, callback_data=f"exec:{device}:{cli_b64}"),
            InlineKeyboardButton("🔄 Change device",     callback_data="change_dev"),
            InlineKeyboardButton("❌ Cancel",             callback_data="cancel"),
        ]
    ])
    await update.message.reply_text(
        f"✅ *Intent:* `{intent}`\n"
        f"📊 Confidence: {bar}\n"
        f"🖥️ Device: *{device}*\n\n"
        f"*CLI to push:*\n```\n{cli}\n```",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# ── Main ─────────────────────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("device",    cmd_device))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("history",   cmd_history))
    app.add_handler(CommandHandler("show",      cmd_show))
    app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if not TELEGRAM_ALLOWED_USERS:
        log.warning(
            "TELEGRAM_ALLOWED_USERS is not set — this bot is OPEN TO ANY Telegram "
            "user and can push config to your devices. Set TELEGRAM_ALLOWED_USERS "
            "in .env to restrict access before going to production."
        )

    log.info("IBN ChatOps Telegram bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
