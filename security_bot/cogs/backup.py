"""
Logging and Backup Management Cog
Handles security event logging and automated server backups.
"""

import discord
from discord.ext import commands, tasks
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from database.db import get_db

logger = logging.getLogger(__name__)


class LoggingAndBackup(commands.Cog):
    """Logging and backup management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = None
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.auto_backup.start()

    async def cog_load(self):
        """Load cog."""
        self.db = get_db()

    @tasks.loop(hours=6)
    async def auto_backup(self):
        """Automatically backup guilds every 6 hours."""
        try:
            logger.info("🔄 Starting automatic backups...")

            for guild in self.bot.guilds:
                try:
                    await self._create_backup(guild)
                except Exception as e:
                    logger.error(f"Backup failed for {guild.name}: {e}")

        except Exception as e:
            logger.error(f"Auto backup error: {e}")

    @auto_backup.before_loop
    async def before_auto_backup(self):
        """Wait for bot ready."""
        await self.bot.wait_until_ready()

    async def _create_backup(self, guild: discord.Guild, backup_type: str = "auto") -> bool:
        """Create server backup."""
        try:
            timestamp = datetime.now(timezone.utc).isoformat().replace(":", "-")
            backup_name = f"{guild.id}_{timestamp}"
            backup_data = {
                "guild_id": guild.id,
                "guild_name": guild.name,
                "created_at": timestamp,
                "backup_type": backup_type,
                "roles": [],
                "channels": [],
                "categories": [],
                "emoji": [],
            }

            # Backup roles
            for role in guild.roles:
                if role == guild.default_role:
                    continue

                backup_data["roles"].append({
                    "name": role.name,
                    "color": str(role.color),
                    "permissions": role.permissions.value,
                    "position": role.position,
                    "hoist": role.hoist,
                    "mentionable": role.mentionable,
                })

            # Backup categories
            for category in guild.categories:
                backup_data["categories"].append({
                    "name": category.name,
                    "position": category.position,
                    "permissions": {
                        str(role.id): role.permissions.value
                        for role in category.overwrites.keys()
                        if isinstance(role, discord.Role)
                    },
                })

            # Backup channels
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    channel_data = {
                        "name": channel.name,
                        "type": "text",
                        "topic": channel.topic,
                        "category": channel.category.name if channel.category else None,
                        "position": channel.position,
                        "nsfw": channel.nsfw,
                    }
                elif isinstance(channel, discord.VoiceChannel):
                    channel_data = {
                        "name": channel.name,
                        "type": "voice",
                        "bitrate": channel.bitrate,
                        "user_limit": channel.user_limit,
                        "category": channel.category.name if channel.category else None,
                        "position": channel.position,
                    }
                else:
                    continue

                backup_data["channels"].append(channel_data)

            # Backup emoji
            for emoji in guild.emojis:
                backup_data["emoji"].append({
                    "name": emoji.name,
                    "url": str(emoji.url),
                })

            # Save backup
            backup_file = self.backup_dir / f"{backup_name}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2)

            # Record in database
            await self.db.record_backup(
                guild.id,
                backup_name,
                backup_type,
                str(backup_file)
            )

            logger.info(f"✅ Backup created: {backup_name}")
            return True

        except Exception as e:
            logger.error(f"Backup creation error: {e}")
            return False

    async def _restore_backup(self, guild: discord.Guild, backup_file: Path) -> bool:
        """Restore server from backup."""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            logger.info(f"🔄 Restoring backup for {guild.name}...")

            # Restore roles (skip @everyone)
            for role_data in backup_data.get("roles", []):
                try:
                    # Check if role exists
                    existing = next((r for r in guild.roles if r.name == role_data["name"]), None)

                    if existing:
                        await existing.edit(
                            color=discord.Color(int(role_data["color"].replace("#", "0x"), 16)),
                            permissions=discord.Permissions(role_data["permissions"]),
                            hoist=role_data["hoist"],
                            mentionable=role_data["mentionable"],
                        )
                        logger.info(f"  ✓ Updated role: {role_data['name']}")
                    else:
                        await guild.create_role(
                            name=role_data["name"],
                            color=discord.Color(int(role_data["color"].replace("#", "0x"), 16)),
                            permissions=discord.Permissions(role_data["permissions"]),
                            hoist=role_data["hoist"],
                            mentionable=role_data["mentionable"],
                        )
                        logger.info(f"  ✓ Created role: {role_data['name']}")

                except Exception as e:
                    logger.warning(f"  ✗ Failed to restore role {role_data['name']}: {e}")

            # Restore categories and channels
            for category_data in backup_data.get("categories", []):
                try:
                    existing_cat = next((c for c in guild.categories if c.name == category_data["name"]), None)

                    if not existing_cat:
                        category = await guild.create_category(category_data["name"])
                        logger.info(f"  ✓ Created category: {category_data['name']}")

                except Exception as e:
                    logger.warning(f"  ✗ Failed to restore category: {e}")

            for channel_data in backup_data.get("channels", []):
                try:
                    existing = next((c for c in guild.channels if c.name == channel_data["name"]), None)

                    if not existing:
                        if channel_data["type"] == "text":
                            await guild.create_text_channel(
                                channel_data["name"],
                                topic=channel_data.get("topic"),
                                nsfw=channel_data.get("nsfw", False),
                            )
                        elif channel_data["type"] == "voice":
                            await guild.create_voice_channel(
                                channel_data["name"],
                                bitrate=channel_data.get("bitrate", 64000),
                                user_limit=channel_data.get("user_limit", 0),
                            )

                        logger.info(f"  ✓ Created channel: {channel_data['name']}")

                except Exception as e:
                    logger.warning(f"  ✗ Failed to restore channel: {e}")

            logger.info(f"✅ Backup restored successfully")
            return True

        except Exception as e:
            logger.error(f"Restore error: {e}")
            return False

    @commands.hybrid_command(name="createbackup", description="Create manual backup")
    @commands.has_permissions(administrator=True)
    async def create_backup(self, ctx: commands.Context):
        """Create manual backup."""
        try:
            async with ctx.typing():
                success = await self._create_backup(ctx.guild, backup_type="manual")

            if success:
                embed = discord.Embed(
                    title="✅ Backup Created",
                    description=f"Server backup saved successfully",
                    color=discord.Color.green(),
                )
            else:
                embed = discord.Embed(
                    title="❌ Backup Failed",
                    color=discord.Color.red(),
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="restore", description="Restore from backup")
    @commands.has_permissions(administrator=True)
    async def restore(self, ctx: commands.Context):
        """Restore server from latest backup."""
        try:
            latest_backup = await self.db.get_latest_backup(ctx.guild.id, "auto")

            if not latest_backup:
                await ctx.send("❌ No backups found for this server.")
                return

            backup_path = Path(latest_backup["file_path"])

            if not backup_path.exists():
                await ctx.send("❌ Backup file not found.")
                return

            # Confirmation
            embed = discord.Embed(
                title="⚠️ Restore Confirmation",
                description="This will restore your server to the latest backup.\n**All current changes will be lost!**",
                color=discord.Color.orange(),
            )

            msg = await ctx.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and reaction.emoji in ["✅", "❌"] and reaction.message.id == msg.id

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)

                if reaction.emoji == "❌":
                    await msg.delete()
                    return

            except asyncio.TimeoutError:
                await msg.delete()
                return

            # Perform restore
            async with ctx.typing():
                success = await self._restore_backup(ctx.guild, backup_path)

            if success:
                embed = discord.Embed(
                    title="✅ Restore Complete",
                    description="Server restored from backup",
                    color=discord.Color.green(),
                )
            else:
                embed = discord.Embed(
                    title="❌ Restore Failed",
                    color=discord.Color.red(),
                )

            await msg.delete()
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="backuplist", description="List all backups")
    @commands.has_permissions(administrator=True)
    async def backup_list(self, ctx: commands.Context):
        """List all backups."""
        try:
            backups = []
            for backup_file in self.backup_dir.glob(f"{ctx.guild.id}_*.json"):
                try:
                    with open(backup_file, 'r') as f:
                        data = json.load(f)
                        backups.append({
                            "name": data.get("guild_name", "Unknown"),
                            "created": data.get("created_at", "Unknown"),
                            "type": data.get("backup_type", "unknown"),
                        })
                except Exception:
                    pass

            if not backups:
                await ctx.send("❌ No backups found.")
                return

            embed = discord.Embed(
                title="📋 Backups",
                color=discord.Color.blue(),
            )

            for i, backup in enumerate(backups[-5:], 1):  # Show last 5
                embed.add_field(
                    name=f"{i}. {backup['name']}",
                    value=f"Type: {backup['type']}\nDate: {backup['created']}",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")


async def setup(bot: commands.Bot):
    """Setup cog."""
    await bot.add_cog(LoggingAndBackup(bot))
