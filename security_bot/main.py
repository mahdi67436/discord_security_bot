"""
Main Bot Entry Point
Military-Grade Discord Security & Anti-Nuke Bot
Production-Ready with Full Security Features
"""

import discord
from discord.ext import commands, tasks
import logging
from pathlib import Path
import os
from typing import Optional
from datetime import datetime, timezone
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
from utils.logger import get_logger

logger = get_logger(__name__)

# Database setup
from database.db import init_database, get_db

# Initialize intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.guild_reactions = True
intents.dm_messages = True

# Bot initialization
class SecurityBot(commands.Bot):
    """Main security bot class with enterprise features."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = None
        self.start_time = None
        self.total_threats_blocked = 0

    async def setup_hook(self):
        """Initialize bot before login."""
        logger.info("🤖 Initializing Security Bot...")

        # Initialize database
        try:
            self.db = await init_database(
                db_type="sqlite",
                db_path="security_bot.db"
            )
            logger.info("✓ Database initialized")
        except Exception as e:
            logger.error(f"✗ Database initialization failed: {e}")
            raise

        # Load cogs
        cogs_dir = Path("cogs")
        if not cogs_dir.exists():
            logger.error("❌ Cogs directory not found!")
            return

        loaded_cogs = 0
        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.name.startswith("_"):
                continue

            cog_name = cog_file.stem
            try:
                await self.load_extension(f"cogs.{cog_name}")
                logger.info(f"✓ Loaded cog: {cog_name}")
                loaded_cogs += 1
            except Exception as e:
                logger.error(f"✗ Failed to load cog {cog_name}: {e}")

        logger.info(f"✓ Loaded {loaded_cogs} security modules")

        # Sync command tree
        try:
            await self.tree.sync()
            logger.info("✓ Slash commands synced globally")
        except Exception as e:
            logger.warning(f"⚠️ Slash command sync issue: {e}")

    async def on_ready(self):
        """Bot is ready."""
        logger.info(
            f"\n{'='*60}"
            f"\n✅ Bot Ready: {self.user}"
            f"\nGuilds: {len(self.guilds)}"
            f"\nUsers: {sum(g.member_count for g in self.guilds)}"
            f"\n{'='*60}\n"
        )

        self.start_time = datetime.now(timezone.utc)
        self.rpc_update.start()

    async def on_guild_join(self, guild: discord.Guild):
        """Handle new guild."""
        logger.info(f"✨ Joined new guild: {guild.name} ({guild.id})")

        try:
            # Initialize guild config
            await self.db.create_guild_config(guild.id)

            # Try to send welcome message to owner
            try:
                embed = discord.Embed(
                    title="🛡️ Security Bot Activated",
                    description="Thank you for adding me to your server!",
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="Quick Start",
                    value="Run `/setup_security` to configure protective systems",
                    inline=False
                )
                embed.add_field(
                    name="Features",
                    value=(
                        "🛡️ Anti-Nuke Protection\n"
                        "🚨 Raid Detection\n"
                        "🔗 Malicious Link Blocker\n"
                        "💬 Multi-Language Content Filter\n"
                        "🤖 Malicious Bot Protection\n"
                        "💾 Auto Backups\n"
                        "📊 Risk Scoring"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="Support",
                    value="Run `!help` for all commands",
                    inline=False
                )

                await guild.owner.send(embed=embed)
            except discord.Forbidden:
                pass

        except Exception as e:
            logger.error(f"Guild join setup error: {e}")

    async def on_guild_remove(self, guild: discord.Guild):
        """Handle guild remove."""
        logger.info(f"👋 Left guild: {guild.name} ({guild.id})")

    @tasks.loop(seconds=30)
    async def rpc_update(self):
        """Update rich presence every 30 seconds."""
        try:
            guild_count = len(self.guilds)
            member_count = sum(g.member_count for g in self.guilds)

            # Rotate between different statuses
            statuses = [
                discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"👁️ {guild_count} Servers"
                ),
                discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"🛡️ {member_count} Users"
                ),
                discord.Activity(
                    type=discord.ActivityType.watching,
                    name="🚨 Anti-Nuke Active"
                ),
                discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"⚠️ {self.total_threats_blocked} Threats Blocked"
                ),
                discord.Activity(
                    type=discord.ActivityType.listening,
                    name="for threats..."
                ),
            ]

            # Cycle through statuses
            status_index = int(datetime.now(timezone.utc).timestamp()) % len(statuses)
            activity = statuses[status_index]

            await self.change_presence(
                status=discord.Status.online,
                activity=activity
            )

        except Exception as e:
            logger.error(f"RPC update error: {e}")

    @rpc_update.before_loop
    async def before_rpc_update(self):
        """Wait for bot to be ready."""
        await self.wait_until_ready()


# Initialize bot
bot = SecurityBot(
    command_prefix=["!", "/"],
    intents=intents,
    help_command=commands.DefaultHelpCommand(),
    sync_commands_debug=False,
)


# Global commands (not in cogs)

@bot.hybrid_command(name="security_status", description="Check bot security status")
async def security_status(ctx: commands.Context):
    """Check security bot status."""
    try:
        uptime = datetime.now(timezone.utc) - bot.start_time if bot.start_time else None
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds // 60) % 60}m" if uptime else "Unknown"

        embed = discord.Embed(
            title="🛡️ Security Bot Status",
            description="Military-Grade Security System",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="Bot",
            value=f"Name: {bot.user.name}\nVersion: 1.0.0-Enterprise",
            inline=False
        )

        embed.add_field(
            name="🌍 Coverage",
            value=f"Servers: {len(bot.guilds)}\nUsers: {sum(g.member_count for g in bot.guilds)}",
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=uptime_str,
            inline=True
        )

        # Get guild config
        config = await bot.db.get_guild_config(ctx.guild.id)
        status_str = (
            f"{'✅' if config.get('antinuke_enabled') else '❌'} Anti-Nuke\n"
            f"{'✅' if config.get('antiraid_enabled') else '❌'} Anti-Raid\n"
            f"{'✅' if config.get('antibot_enabled') else '❌'} Bot Protection\n"
            f"{'✅' if config.get('antibadword_enabled') else '❌'} Content Filter\n"
            f"{'✅' if config.get('antilink_enabled') else '❌'} Link Detection"
        )

        embed.add_field(
            name="🔐 Active Systems",
            value=status_str,
            inline=False
        )

        embed.add_field(
            name="📊 Threat Level",
            value=f"Threats Blocked: {bot.total_threats_blocked}",
            inline=False
        )

        embed.timestamp = datetime.now(timezone.utc)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.hybrid_command(name="lockdown", description="Activate emergency lockdown")
@commands.has_permissions(administrator=True)
async def lockdown(ctx: commands.Context):
    """Activate emergency server lockdown."""
    try:
        config = await bot.db.get_guild_config(ctx.guild.id)

        # Lock all channels
        locked = 0
        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(
                    ctx.guild.default_role,
                    send_messages=False,
                    add_reactions=False,
                    connect=False,
                )
                locked += 1
            except (discord.Forbidden, discord.HTTPException):
                pass

        await bot.db.update_guild_config(ctx.guild.id, lockdown_mode=True)

        embed = discord.Embed(
            title="🔒 LOCKDOWN ACTIVATED",
            description=f"Server is locked. {locked} channels restricted.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Use", value="Use `!unlock` to restore access", inline=False)

        await ctx.send(embed=embed)
        logger.warning(f"🔒 Lockdown activated in {ctx.guild.name}")

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.hybrid_command(name="unlock", description="Exit emergency lockdown")
@commands.has_permissions(administrator=True)
async def unlock(ctx: commands.Context):
    """Exit emergency lockdown."""
    try:
        config = await bot.db.get_guild_config(ctx.guild.id)

        if not config.get("lockdown_mode"):
            await ctx.send("Server is not in lockdown.")
            return

        # Restore permissions
        restored = 0
        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(
                    ctx.guild.default_role,
                    send_messages=None,
                    add_reactions=None,
                    connect=None,
                )
                restored += 1
            except (discord.Forbidden, discord.HTTPException):
                pass

        await bot.db.update_guild_config(ctx.guild.id, lockdown_mode=False)

        embed = discord.Embed(
            title="🔓 Lockdown Lifted",
            description=f"Server unlocked. {restored} channels restored.",
            color=discord.Color.green(),
        )

        await ctx.send(embed=embed)
        logger.info(f"🔓 Lockdown lifted in {ctx.guild.name}")

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Handle command errors."""
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You don't have permission to use this command.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Missing Argument",
            description=f"Missing required argument: `{error.param.name}`",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
    else:
        logger.error(f"Command error: {error}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)[:100]}",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)


async def main():
    """Main entry point."""
    # Get token
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("❌ DISCORD_TOKEN not found in .env file")
        return

    # Start bot
    try:
        async with bot:
            await bot.start(token)
    except discord.LoginFailure:
        logger.error("❌ Invalid token provided")
    except KeyboardInterrupt:
        logger.info("⚙️ Bot shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        logger.info("👋 Bot stopping...")


if __name__ == "__main__":
    import sys

    # Check Python version
    if sys.version_info < (3, 11):
        logger.error("❌ Python 3.11+ required")
        sys.exit(1)

    logger.info(
        "\n" + "="*60
        + "\n🛡️  MILITARY-GRADE SECURITY BOT"
        + "\nVersion: 1.0.0 Enterprise"
        + "\nStatus: Starting..."
        + "\n" + "="*60 + "\n"
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user")
