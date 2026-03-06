# main.py - Discord Raid Detector Bot with forced presence & better gateway debug
# Fixes for "logged in but offline/no green dot" on hosted platforms

import discord
from discord.ext import commands
import datetime
from collections import deque
import os
import asyncio
import time
from dotenv import load_dotenv

load_dotenv()  # for local; on host use env vars

# ── Config ──
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN is missing in environment variables!")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))  # 0 = all servers
MIN_ACCOUNT_AGE_DAYS = 7
JOIN_WINDOW_SECONDS = 60
MAX_JOINS_IN_WINDOW = 5
TIMEOUT_MINUTES = 10
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID", "0"))

recent_joins = deque(maxlen=200)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] ✅ Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'Watching guild(s): {"All" if GUILD_ID == 0 else GUILD_ID}')
    
    # Force online status + activity (fixes many "invisible online" cases)
    await bot.change_presence(
        status=discord.Status.online,
        afk=False,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for raids | !status"
        )
    )
    print("Presence forced to ONLINE – check Discord member list now.")

@bot.event
async def on_connect():
    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] Gateway connected")

@bot.event
async def on_disconnect():
    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] !!! Gateway DISCONNECTED – possible token/intents/rate limit issue')

@bot.event
async def on_resumed():
    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] Gateway RESUMED – connection restored')

@bot.event
async def on_error(event, *args, **kwargs):
    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] ERROR in event {event}: {args} {kwargs}')

# Your raid detection (add your full on_member_join logic here if different)
@bot.event
async def on_member_join(member: discord.Member):
    if GUILD_ID != 0 and member.guild.id != GUILD_ID:
        return

    now = datetime.datetime.now(datetime.UTC)
    account_age_days = (now - member.created_at).days

    recent_joins.append(now)
    while recent_joins and (now - recent_joins[0]).total_seconds() > JOIN_WINDOW_SECONDS:
        recent_joins.popleft()

    is_mass = len(recent_joins) > MAX_JOINS_IN_WINDOW
    is_young = account_age_days < MIN_ACCOUNT_AGE_DAYS

    if is_young or is_mass:
        duration = datetime.timedelta(minutes=TIMEOUT_MINUTES)
        reason = f"Suspicious: age={account_age_days}d | mass_join={is_mass}"
        try:
            await member.timeout_for(duration=duration, reason=reason)
            print(f"Timed out {member} ({member.id}) - {reason}")
            if MOD_CHANNEL_ID:
                ch = bot.get_channel(MOD_CHANNEL_ID)
                if ch:
                    await ch.send(f"🚨 Timed out {member.mention}: {reason}")
        except Exception as e:
            print(f"Timeout failed for {member}: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def status(ctx):
    await ctx.send(
        f"**Guardian Bot Status**\n"
        f"Online (per code): Yes\n"
        f"Uptime: Running since login\n"
        f"Recent joins tracked: {len(recent_joins)}\n"
        f"Check member list for green dot."
    )

# Periodic log to keep activity visible in container logs
async def log_activity():
    while True:
        await asyncio.sleep(60)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat – bot still running, recent joins: {len(recent_joins)}")

async def main():
    asyncio.create_task(log_activity())
    await bot.start(BOT_TOKEN, reconnect=True)

if __name__ == "__main__":
    print("Starting bot with forced presence & debug logging...")
    asyncio.run(main())
