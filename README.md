# Discord Suspicious Account Detector Bot

Simple, lightweight Discord bot that timeouts potentially fake/raid accounts on join.

**Features**
- Detects young accounts (configurable min age)
- Detects mass joins (raid pattern)
- Applies custom-length timeout
- Optional mod channel notification
- In-memory only (no DB needed for small servers)

**Legal note**: Only acts inside your own server. Complies with Discord ToS when used responsibly.

## Setup

1. Create a bot at https://discord.com/developers/applications
   - Enable **Server Members Intent**
   - Invite with: `bot` scope + **Moderate Members** permission

2. Clone this repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/discord-raid-detector.git
   cd discord-raid-detector
