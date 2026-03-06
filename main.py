# main.py
# Discord Raid/Suspicious Account Detector Bot
# Detects young accounts + mass joins → applies custom timeout
# Updated: Full intents fix, disconnect logging, better debug output

import discord
from discord.ext import commands
import datetime
from collections import deque
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file (for local testing; ignored on host via env vars)

# ── Configuration ── (edit these or override via env vars)
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))                  # 0 = act in all servers (recommended: set your ID)
MIN_ACCOUNT_AGE_DAYS = 7
JOIN_WINDOW_SECONDS = 60
MAX_JOINS_IN_WINDOW = 5
TIMEOUT_MINUTES = 10
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID", "0"))      # Set to 0 to disable notifications

# In-memory join tracker (efficient for most servers)
recent_joins = deque(maxlen=200)

# ── Intents ── (both privileged ones needed: members for joins, message_content for commands)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # REQUIRED for prefix commands like !status to read message text

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'✅ Logged in successfully as {bot.user} (ID: {bot.user.id})')
    print(f'Watching server(s): {"All" if GUILD_ID == 0 else GUILD_ID}')
    print('Monitoring for suspicious joins... Ready!')

@bot.event
async def on_disconnect():
    print("!!! WARNING: Bot disconnected from Discord gateway !!! Check network/token/intents.")

@bot.event
async def on_resumed():
    print("Bot successfully resumed connection to Discord gateway.")

@bot.event
async def on_member_join(member: discord.Member):
    if GUILD_ID != 0 and member.guild.id != GUILD_ID:
        return

    now = datetime.datetime.now(datetime.UTC)
    account_age_days = (now - member.created_at).days

    recent_joins.append(now)

    # Clean old joins
    while recent_joins and (now - recent_joins[0]).total_seconds() > JOIN_WINDOW_SECONDS:
        recent_joins.popleft()

    is_mass_join = len(recent_joins) > MAX_JOINS_IN_WINDOW
    is_young = account_age_days < MIN_ACCOUNT_AGE_DAYS

    if is_young or is_mass_join:
        duration = datetime.timedelta(minutes=TIMEOUT_MINUTES)
        reason = f"Suspicious join: age={account_age_days}d | mass_join={is_mass_join}"

        try:
            await member.timeout_for(duration=duration, reason=reason)
            print(f"Timed out {member} ({member.id}) → {reason}")

            if MOD_CHANNEL_ID != 0:
                channel = bot.get_channel(MOD_CHANNEL_ID)
                if channel:
                    await channel.send(
                        f"🚨 **Timed out** {member.mention} ({member.id})\n"
                        f"Reason: {reason}\n"
                        f"Created: {member.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
                    )
        except discord.Forbidden:
            print(f"Permission error: Cannot timeout {member}. Check bot role hierarchy + Moderate Members perm.")
        except Exception as e:
            print(f"Error during timeout of {member}: {e}")

# ── Simple test command ── (should work after intents fix)
@bot.command()
@commands.has_permissions(administrator=True)
async def status(ctx):
    recent_count = len(recent_joins)
    await ctx.send(
        f"**Bot Status**\n"
        f"Online: Yes\n"
        f"Tracking joins: {recent_count} in last window\n"
        f"Config: Age < {MIN_ACCOUNT_AGE_DAYS}d | Max joins {MAX_JOINS_IN_WINDOW}/{JOIN_WINDOW_SECONDS}s\n"
        f"Timeout: {TIMEOUT_MINUTES} min"
    )

# ── Run the bot ──
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN is missing! Set it in Environment Variables on JustRunMy.App or .env locally.")
    
    print("Starting bot...")
    bot.run(BOT_TOKEN, reconnect=True)  # Explicit reconnect=True (default anyway)
