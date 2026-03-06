# main.py
# Discord Raid Detector Bot + Simple Web Dashboard (Flask)
# Run bot async + web server in same process

import discord
from discord.ext import commands
import datetime
from collections import deque
import os
from dotenv import load_dotenv
import asyncio
import threading
from flask import Flask, render_template_string, jsonify
import time

load_dotenv()

# ── Config ──
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
MIN_ACCOUNT_AGE_DAYS = 7
JOIN_WINDOW_SECONDS = 60
MAX_JOINS_IN_WINDOW = 5
TIMEOUT_MINUTES = 10
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID", "0"))

recent_joins = deque(maxlen=200)

# Status tracking for web panel
bot_status = {
    "online": False,
    "last_login": None,
    "last_disconnect": None,
    "disconnect_reason": "Unknown",
    "uptime_start": None,
    "recent_joins_count": 0
}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ── Discord Events ──
@bot.event
async def on_ready():
    now = datetime.datetime.now(datetime.UTC)
    bot_status["online"] = True
    bot_status["last_login"] = now.isoformat()
    bot_status["uptime_start"] = time.time()
    bot_status["disconnect_reason"] = "Connected successfully"
    print(f'✅ Bot online: {bot.user}')

@bot.event
async def on_disconnect():
    now = datetime.datetime.now(datetime.UTC)
    bot_status["online"] = False
    bot_status["last_disconnect"] = now.isoformat()
    bot_status["disconnect_reason"] = "Gateway disconnected (check token/intents/network)"
    print("!!! Bot disconnected !!!")

@bot.event
async def on_resumed():
    bot_status["online"] = True
    bot_status["disconnect_reason"] = "Reconnected to gateway"
    print("Bot resumed")

# Your on_member_join logic (unchanged, abbreviated for brevity)
@bot.event
async def on_member_join(member: discord.Member):
    # ... (your existing timeout logic here) ...
    bot_status["recent_joins_count"] = len(recent_joins)

@bot.command()
@commands.has_permissions(administrator=True)
async def status(ctx):
    await ctx.send(f"Bot online: {bot_status['online']}\nLast disconnect: {bot_status.get('disconnect_reason', 'N/A')}")

# ── Flask Web Dashboard ──
web_app = Flask(__name__)

@web_app.route('/')
def dashboard():
    uptime = "N/A"
    if bot_status["uptime_start"]:
        seconds = time.time() - bot_status["uptime_start"]
        uptime = f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m {int(seconds % 60)}s"

    html = f"""
    <html>
    <head><title>Bot Guardian Panel</title></head>
    <body>
        <h1>Guardian Bot Dashboard</h1>
        <p><strong>Status:</strong> {"Online 🟢" if bot_status["online"] else "Offline 🔴"}</p>
        <p><strong>Why offline (if applicable):</strong> {bot_status["disconnect_reason"]}</p>
        <p><strong>Last login:</strong> {bot_status.get("last_login", "Never")}</p>
        <p><strong>Last disconnect:</strong> {bot_status.get("last_disconnect", "N/A")}</p>
        <p><strong>Uptime:</strong> {uptime}</p>
        <p><strong>Recent joins tracked:</strong> {bot_status["recent_joins_count"]}</p>
        <p><strong>Config:</strong> Age < {MIN_ACCOUNT_AGE_DAYS}d | Max joins {MAX_JOINS_IN_WINDOW}/{JOIN_WINDOW_SECONDS}s | Timeout {TIMEOUT_MINUTES} min</p>
        <hr>
        <p>Refresh page for updates. Check JustRunMy.app logs for detailed errors.</p>
    </body>
    </html>
    """
    return render_template_string(html)

@web_app.route('/api/status')
def api_status():
    return jsonify(bot_status)

# ── Run bot + web server ──
def run_flask():
    web_app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

async def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("Web dashboard started on port 8080")
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN missing!")
    
    # JustRunMy.app will expose port 8080 as HTTPS automatically
    asyncio.run(main())
