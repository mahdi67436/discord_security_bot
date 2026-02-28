# 🚀 Quick Start Guide

Get your Discord security bot running in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- A Discord server where you're admin
- A text editor

## Step 1: Create Discord Bot Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Name it (e.g., "Security Bot")
4. Go to **"Bot"** tab → Click **"Add Bot"**
5. Under **TOKEN**, click **"Copy"**
6. Paste somewhere safe temporarily

## Step 2: Set Bot Permissions

1. In Developer Portal, go to **OAuth2** → **URL Generator**
2. Select **Scopes**: `bot`, `applications.commands`
3. Select **Permissions**:
   - Administrator ✓
   - (or individually: Manage Channels, Manage Roles, Ban/Kick Members, Moderate Members, etc.)
4. Copy the generated URL and open in browser
5. Select your server and authorize

**Bot is now invited to your server** ✅

## Step 3: Setup Bot Files

```bash
# 1. Navigate to your folder
cd security_bot

# 2. Create virtual environment
python -m venv venv

# 3. Activate it
# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

# 4. Install packages
pip install -r requirements.txt
```

## Step 4: Configure Bot

```bash
# Copy example config
cp .env.example .env
```

Edit `.env` file with a text editor:

```
DISCORD_TOKEN=paste_your_token_here
```

That's it! Other settings have good defaults.

## Step 5: Run Bot

```bash
python main.py
```

You should see:

```
============================================================
🛡️  MILITARY-GRADE SECURITY BOT
Version: 1.0.0 Enterprise
Status: Starting...
============================================================

✓ Database initialized
✓ Loaded security modules...
✓ Slash commands synced

============================================================
✅ Bot Ready: YourBotName#0000
Guilds: 1
Users: 25
============================================================
```

**Bot is running!** 🎉

## Step 6: Secure Your Server

In Discord, run:

```
/setup_security
```

The bot will automatically:
- ✅ Create security role
- ✅ Create log channel
- ✅ Enable all protections
- ✅ Setup backups

**Done!** Your server is now protected. 🛡️

---

## Common First Commands

```
/security_status          # Check system
/security_report          # Detailed report
/warn @user reason        # Warn user
/createbackup             # Backup server
/help                     # List all commands
```

---

## Need Help?

- Check `README.md` for full documentation
- See `CONFIGURATION.md` for advanced setup
- Look at `logs/security_bot.log` for errors
- Check #security-logs channel for events

---

## Keeping Bot Running

### Option 1: Screen Terminal (Linux/Mac/Windows-WSL)

```bash
screen -S security-bot
python main.py

# Press Ctrl+A then D to detach
# Later: screen -r security-bot  (reattach)
```

### Option 2: Background Service (Linux)

Create `/etc/systemd/system/security-bot.service`:

```ini
[Unit]
Description=Discord Security Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/security_bot
ExecStart=/path/to/security_bot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable security-bot
sudo systemctl start security-bot
sudo systemctl status security-bot
```

### Option 3: Docker (Any Platform)

```bash
docker build -t security-bot .
docker run -d --env-file .env --name security-bot security-bot
```

### Option 4: Cloud (Easiest)

Deploy to **Railway.app**, **Render.com**, or **Heroku**:

1. Push code to GitHub
2. Connect platform to GitHub
3. Add `DISCORD_TOKEN` environment variable
4. Deploy!

See `README.md` for detailed cloud setup.

---

## Troubleshooting

### Bot won't start

```bash
# Check Python version
python --version

# Check token in .env file
cat .env

# Run with debug output
python -u main.py
```

### Commands not appearing in Discord

- Wait 60 seconds after startup
- Try typing `/` to see slash commands
- Make sure bot has permissions
- Check #security-logs for errors

### Database error

```bash
# SQLite - remove old database
rm security_bot.db

# Restart bot - it will recreate database
python main.py
```

---

## Next Steps

1. **Review Settings**
   - Check log channel: #security-logs
   - Verify backup creation
   - Test `/warn` command

2. **Add Moderators**
   - Give trusted users the "🛡️ Security Bot" role
   - They can use moderation commands

3. **Customize Filtering**
   - `/addcustomword` for your own badwords
   - `/addwhitelist` for trusted users

4. **Monitor Daily**
   - Run `/security_report` 
   - Check #security-logs for threats

5. **Stay Updated**
   - Check GitHub for updates
   - Update dependencies: `pip install --upgrade -r requirements.txt`

---

## Features at a Glance

🛡️ **Anti-Nuke** - Stops mass deletion of channels/roles
🚨 **Raid Detection** - Auto-locks server during raids
💬 **Content Filter** - Multi-language profanity detection
🔗 **Link Blocker** - Stops malicious/phishing links
🤖 **Bot Protection** - Auto-removes dangerous bots
💾 **Auto Backups** - Saves server state every 6 hours
📊 **Risk Scoring** - Tracks user behavior
🔒 **Lockdown Mode** - Emergency server freeze

---

## Support

- 📖 **Documentation**: README.md, CONFIGURATION.md
- 🐛 **Issues**: Check GitHub or create issue
- 💬 **Logs**: See `logs/security_bot.log` for details
- 🆘 **Help**: Post in #security-logs channel

---

**Everything working?** You're awesome! 🎉

Enjoy your secure server! 🛡️

*Last updated: February 2026*
