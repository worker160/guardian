# main.py
# Discord bot to detect & timeout suspicious/fake accounts on join
# Features: young account check + mass-join (raid) detection
# Safe, in-server only, no external tracking

import discord
from discord.ext import commands
import datetime
from collections import deque
import os
from dotenv import load_dotenv

load_dotenv()  # Loads .env file

# ── Configuration ── (customize here or move to .env later)
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")          # Required from .env
GUILD_ID = int(os.getenv("GUILD_ID", "0"))          # Your server ID (optional fallback)
MIN_ACCOUNT_AGE_DAYS = 7                            # Younger = suspicious
JOIN_WINDOW_SECONDS = 60                            # Sliding window for mass joins
MAX_JOINS_IN_WINDOW = 5                             # Threshold for "raid"
TIMEOUT_MINUTES = 10                                # Custom timeout length
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID", "0"))  # Optional: channel to notify

# In-memory recent joins (efficient for small/medium servers)
recent_joins = deque(maxlen=200)

intents = discord.Intents.default()
intents.members = True  # For member join events
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user} (ID: {bot.user.id})')
    print('Monitoring joins for suspicious activity...')
    if GUILD_ID == 0:
        print("Warning: GUILD_ID not set in .env — acting in all servers (single-guild recommended)")

@bot.event
async def on_member_join(member: discord.Member):
    if GUILD_ID != 0 and member.guild.id != GUILD_ID:
        return

    now = datetime.datetime.now(datetime.UTC)
    account_age_days = (now - member.created_at).days

    # Record join time
    recent_joins.append(now)

    # Remove old joins outside window
    while recent_joins and (now - recent_joins[0]).total_seconds() > JOIN_WINDOW_SECONDS:
        recent_joins.popleft()

    is_mass_join = len(recent_joins) > MAX_JOINS_IN_WINDOW
    is_young = account_age_days < MIN_ACCOUNT_AGE_DAYS

    if is_young or is_mass_join:
        duration = datetime.timedelta(minutes=TIMEOUT_MINUTES)
        reason = f"Suspicious: age={account_age_days}d | mass_join={is_mass_join}"

        try:
            await member.timeout_for(duration=duration, reason=reason)
            print(f"Timed out {member} ({member.id}) | {reason}")

            if MOD_CHANNEL_ID != 0:
                mod_channel = bot.get_channel(MOD_CHANNEL_ID)
                if mod_channel:
                    await mod_channel.send(
                        f"🚨 **Timed out** {member.mention} ({member.id})\n"
                        f"→ Reason: {reason}\n"
                        f"→ Account created: {member.created_at.strftime('%Y-%m-%d')}"
                    )
        except discord.Forbidden:
            print(f"Missing permissions to timeout {member}")
        except Exception as e:
            print(f"Error timing out {member}: {e}")

# ── Optional: Simple status command ──
@bot.command()
@commands.has_permissions(administrator=True)
async def status(ctx):
    await ctx.send(f"Bot online • Watching for raids • {len(recent_joins)} recent joins tracked")

if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN not found in .env!")
    bot.run(BOT_TOKEN)
