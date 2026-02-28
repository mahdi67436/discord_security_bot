# Configuration Guide

## Complete Setup Instructions

### 1. Initial Setup

#### Create `.env` File

```bash
cp .env.example .env
```

Edit `.env`:

```env
# REQUIRED
DISCORD_TOKEN=your_token_here
BOT_OWNER_ID=your_discord_id

# OPTIONAL - Database (leave as-is for SQLite)
DB_TYPE=sqlite
DB_NAME=security_bot.db
```

#### Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

#### Run Bot

```bash
python main.py
```

---

### 2. First-Time Server Setup

Once bot joins your server:

```
/setup_security
```

This automatically:
- Creates security role (🛡️ Security Bot)
- Creates log channel (#security-logs)
- Enables all protection systems
- Creates verification channel

---

### 3. Customization

#### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DISCORD_TOKEN` | Bot token | Required |
| `BOT_OWNER_ID` | Owner Discord ID | Optional |
| `ENVIRONMENT` | dev/production | development |
| `DEBUG` | Verbose logging | False |
| `DB_TYPE` | sqlite/postgresql | sqlite |
| `LOG_LEVEL` | DEBUG/INFO/WARNING | INFO |

#### Database Configuration

**SQLite (Development/Default)**

```env
DB_TYPE=sqlite
DB_NAME=security_bot.db
```

- Simple, no setup
- Good for single server/testing
- File-based storage

**PostgreSQL (Production)**

```env
DB_TYPE=postgresql
DATABASE_URL=postgresql://user:password@localhost:5432/security_bot
```

- Scalable to 10,000+ servers
- Multi-bot support
- Better performance

To set up PostgreSQL:

```bash
# Install PostgreSQL

# Create database
createdb security_bot
createuser security_bot
psql security_bot << EOF
ALTER USER security_bot WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE security_bot TO security_bot;
EOF

# Update .env
DATABASE_URL=postgresql://security_bot:strong_password@localhost:5432/security_bot
```

#### Security Thresholds

Edit `cogs/antinuke.py`:

```python
# Adjust thresholds (default values shown)
CHANNEL_DELETE_THRESHOLD = 3      # channels
CHANNEL_CREATE_THRESHOLD = 5      # channels
ROLE_DELETE_THRESHOLD = 3         # roles
ROLE_CREATE_THRESHOLD = 5         # roles
WEBHOOK_CREATE_THRESHOLD = 5      # webhooks
TIME_WINDOW = 30                  # seconds
```

Lower values = more sensitive detection but higher false positives

Edit `cogs/antiraid.py`:

```python
JOINS_PER_MINUTE = 5              # suspicious join rate
MAX_YOUNG_ACCOUNTS = 10           # young accounts before lockdown
YOUNG_ACCOUNT_DAYS = 7            # account age threshold
```

Edit `cogs/moderation.py` for spam filter:

```python
self.spam_filter = SpamFilter(
    max_messages=5,      # messages allowed
    time_window=5        # in 5 seconds
)
```

---

### 4. Per-Server Configuration

Use commands to customize each server:

#### Toggle Security Systems

```
/toggle_system antinuke true       # Enable anti-nuke
/toggle_system antiraid true       # Enable raid detection
/toggle_system antibot true        # Enable bot protection
/toggle_system badword true        # Enable profanity filter
/toggle_system antilink true       # Enable link blocking
```

#### Add Custom Badwords

```
/addcustomword slur medium         # Add custom word
/removecustomword slur             # Remove word
```

#### Whitelist Management

```
# Whitelist trusted users (won't be affected by protections)
/addwhitelist @user_name "Admin account"
/removewhitelist @user_name

# Bot whitelist (prevent auto-kick)
# Use via database or admin panel
```

#### Risk Scoring

View user risk status:

```
/getrisk @user
```

Risk levels:
- 🟢 0-20: Low (Monitor)
- 🟡 21-50: Medium (Watch)
- 🔴 51-75: High (Restrict/Warn)
- 🔴🔴 76-100: Critical (Ban recommended)

---

### 5. Logging Setup

Logs are stored in `logs/` directory:

```
logs/
  └── security_bot.log    # Main application log
```

View logs:

```bash
# Current logs
tail -f logs/security_bot.log

# Specific time
grep "2024-02-28" logs/security_bot.log

# Only errors
grep "ERROR" logs/security_bot.log
```

Log levels in `.env`:

```env
LOG_LEVEL=INFO           # Default
LOG_LEVEL=DEBUG          # Verbose, for troubleshooting
LOG_LEVEL=WARNING        # Warnings + errors only
```

---

### 6. Backup Configuration

Automatic backups every 6 hours to `backups/` folder

Manual backup:

```
/createbackup
```

View backups:

```
/backuplist
```

Restore from backup:

```
/restore
```

Backup storage structure:

```
backups/
  └── <guild_id>_<timestamp>.json
      ├── guild_id
      ├── guild_name
      ├── roles     (all roles data)
      ├── channels  (all channels data)
      ├── categories
      └── emoji
```

---

### 7. Deployment Configuration

#### Local Machine

Ready to go! Just:

```bash
cp .env.example .env
pip install -r requirements.txt
python main.py
```

#### VPS (Linux - Ubuntu/Debian)

```bash
# Install Python
sudo apt update
sudo apt install python3.11 python3.11-venv

# Clone repo
git clone <your-repo>
cd security_bot

# Setup
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy config
cp .env.example .env
# Edit .env with your token

# Run (with screen for background)
screen -S security-bot
python main.py
```

#### Docker (Any Platform)

```bash
# Build image
docker build -t security-bot .

# Run container
docker run -d \
  --name security-bot \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/backups:/app/backups \
  security-bot
```

#### Docker Compose (Recommended for Production)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

#### Railway.app

1. Push to GitHub
2. Create Railway project
3. Connect GitHub repo
4. Add environment variables:
   - `DISCORD_TOKEN`
   - `ENVIRONMENT=production`
5. Deploy

#### Render.com

1. Create `render.yaml`:

```yaml
services:
  - type: web
    name: security-bot
    runtime: python
    plan: free
    startCommand: python main.py
    envVars:
      - key: DISCORD_TOKEN
        sync: false
      - key: ENVIRONMENT
        value: production
```

2. Connect GitHub repo
3. Deploy

---

### 8. Monitoring & Maintenance

#### Daily Checks

```
/security_status         # Check system health
/security_report         # Get detailed report
```

#### Weekly Tasks

- Review security logs (#security-logs channel)
- Check for high-risk users (`/getrisk` random users)
- Verify backups are being created

#### Monthly Tasks

- Rotate Discord bot token (Developer Portal)
- Update dependencies:

```bash
pip install --upgrade -r requirements.txt
```

- Review and update badword filters
- Check database size

---

### 9. Performance Tuning

For high-traffic servers (1000+ members, 100+ messages/second):

#### Increase Threads

In `main.py`, increasing connection pool:

```python
# Already optimized for asyncio, no thread pool needed
# The bot uses async operations exclusively
```

#### Database Optimization

For PostgreSQL:

```sql
-- Create indexes (run once)
CREATE INDEX idx_guild_id ON user_warnings(guild_id);
CREATE INDEX idx_user_id ON user_warnings(user_id);
CREATE INDEX idx_timestamp ON audit_log_cache(timestamp);
```

#### Message Filtering

For very high message volume (1000+/sec), consider:

```python
# Increase cache size (in moderation.py)
self.spam_filter = SpamFilter(
    max_messages=10,     # Increased from 5
    time_window=10       # Increased from 5
)
```

---

### 10. Troubleshooting

**Bot Won't Start**

```bash
# Check Python version
python --version  # Should be 3.11+

# Check token
echo $DISCORD_TOKEN  # Should show token (Windows: echo %DISCORD_TOKEN%)

# Check dependencies  
pip list | grep discord  # Should show discord.py 2.3+

# Run with verbose output
python -u main.py 2>&1 | tee bot.log
```

**Commands Not Working**

```
1. Check bot permissions (should have Administrator)
2. Verify slash commands synced (automatic on startup)
3. Wait 60 seconds for Discord to sync
4. Check server logs: /security_logs
```

**High CPU/Memory**

```
1. Check message count (toggle filtering if needed)
2. Review database queries
3. Check for memory leaks (restart bot periodically)
4. Monitor with: top (Linux) / Task Manager (Windows)
```

**Database Issues**

```bash
# SQLite - backup and reset
cp security_bot.db security_bot.db.bak
rm security_bot.db
python main.py  # Creates new database

# PostgreSQL - check connection
psql -U security_bot -h localhost -d security_bot
```

---

## Advanced Configuration

### Custom Behavior Patterns

Modify `utils/risk_engine.py` to adjust risk calculations:

```python
# Increase risk for new account detection
RISK_DELTAS = {
    "badword_violation": 10.0,      # Increased from 5
    "raid_attempt": 50.0,           # Increased from 30
}
```

### Adding Custom Features

Create new cog in `cogs/`:

```python
import discord
from discord.ext import commands

class MyFeature(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None

    @commands.Cog.listener()
    async def on_message(self, message):
        pass

async def setup(bot):
    await bot.add_cog(MyFeature(bot))
```

---

## Security Best Practices

✅ **DO:**
- Keep `.env` file secret (add to `.gitignore`)
- Use strong database passwords for PostgreSQL
- Rotate Discord token regularly
- Update dependencies monthly
- Review security logs weekly

❌ **DON'T:**
- Share `.env` file
- Commit token to GitHub
- Use default passwords
- Run old versions
- Disable security features in production

---

## Support

Need help? Check:
1. README.md - General documentation
2. Inline code comments - Implementation details
3. Logs (`logs/security_bot.log`) - Error messages
4. `.env.example` - Configuration template

For issues, create detailed bug report with:
- Error message
- Steps to reproduce
- Log file excerpt
- Server configuration details
