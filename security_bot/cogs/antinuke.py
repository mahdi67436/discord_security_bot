"""
Advanced Anti-Nuke Cog - Real-time protection against server destruction.
Detects and prevents mass channel/role deletion, webhook abuse, and permission escalation.
"""

import discord
from discord.ext import commands, tasks
import logging
from typing import Dict, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from database.db import get_db
from utils.permissions import PermissionValidator
from utils.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class AntiNuke(commands.Cog):
    """Anti-nuke security system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = None
        # Track actions per user in time windows
        self.action_cache: Dict[int, List[Dict]] = defaultdict(list)
        self.audit_monitor.start()

    async def cog_load(self):
        """Load cog."""
        self.db = get_db()

    # Thresholds for detection
    CHANNEL_DELETE_THRESHOLD = 3  # 3 channels in time window
    CHANNEL_CREATE_THRESHOLD = 5  # 5 channels in time window
    ROLE_DELETE_THRESHOLD = 3     # 3 roles in time window
    ROLE_CREATE_THRESHOLD = 5     # 5 roles in time window
    WEBHOOK_CREATE_THRESHOLD = 5  # 5 webhooks in time window
    TIME_WINDOW = 30  # seconds

    async def _check_thresholds(self, user_id: int, action_type: str,
                                guild_id: int) -> bool:
        """Check if user exceeded action thresholds."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.TIME_WINDOW)

        # Clean old entries
        if user_id in self.action_cache:
            self.action_cache[user_id] = [
                a for a in self.action_cache[user_id]
                if a["timestamp"] > cutoff and a["guild_id"] == guild_id
            ]

        # Get threshold for action type
        thresholds = {
            "channel_delete": self.CHANNEL_DELETE_THRESHOLD,
            "channel_create": self.CHANNEL_CREATE_THRESHOLD,
            "role_delete": self.ROLE_DELETE_THRESHOLD,
            "role_create": self.ROLE_CREATE_THRESHOLD,
            "webhook_create": self.WEBHOOK_CREATE_THRESHOLD,
        }

        current_count = len([
            a for a in self.action_cache[user_id]
            if a["type"] == action_type
        ])

        threshold = thresholds.get(action_type, 5)

        if current_count >= threshold:
            return True  # Threshold exceeded

        # Add to cache
        self.action_cache[user_id].append({
            "type": action_type,
            "timestamp": now,
            "guild_id": guild_id,
        })

        return False

    async def _perform_lockdown(self, guild: discord.Guild, attacker_id: int,
                               reason: str):
        """Perform emergency server lockdown."""
        try:
            # Get security role
            config = await self.db.get_guild_config(guild.id)
            security_role_id = config.get("security_role_id")
            log_channel_id = config.get("log_channel_id")

            # Update @everyone permissions to read-only
            for channel in guild.channels:
                try:
                    await channel.set_permissions(
                        guild.default_role,
                        send_messages=False,
                        add_reactions=False,
                        connect=False,
                    )
                except discord.Forbidden:
                    pass

            # Ban the attacker if not owner
            try:
                attacker = guild.get_member(attacker_id)
                if attacker and attacker.id != guild.owner_id:
                    await guild.ban(attacker, reason=f"[AUTO-BAN] {reason}")
                    logger.warning(f"🚫 Auto-banned {attacker} in {guild.name}")
            except discord.Forbidden:
                pass

            # Log to security channel
            if log_channel_id:
                try:
                    log_channel = guild.get_channel(log_channel_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="🚨 LOCKDOWN ACTIVATED",
                            description=f"Server entered emergency lockdown",
                            color=discord.Color.red(),
                        )
                        embed.add_field(name="Reason", value=reason, inline=False)
                        embed.add_field(name="Attacker", value=f"<@{attacker_id}>", inline=False)
                        embed.timestamp = datetime.now(timezone.utc)
                        await log_channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to send lockdown log: {e}")

            # Update database
            await self.db.update_guild_config(guild.id, lockdown_mode=True)

            # Notify owner
            try:
                await guild.owner.send(
                    f"🚨 **SERVER LOCKDOWN ACTIVATED**\n"
                    f"Guild: {guild.name}\n"
                    f"Reason: {reason}\n"
                    f"Use `!unlock` to restore normalcy."
                )
            except discord.Forbidden:
                pass

        except Exception as e:
            logger.error(f"Lockdown failed: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Monitor channel deletion."""
        try:
            config = await self.db.get_guild_config(channel.guild.id)

            if not config.get("antinuke_enabled"):
                return

            # Get audit log entry
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                user_id = entry.user.id

                # Check whitelist
                is_whitelisted = await self.db.is_user_whitelisted(channel.guild.id, user_id)
                if is_whitelisted or user_id == channel.guild.owner_id:
                    return

                # Check threshold
                threshold_exceeded = await self._check_thresholds(
                    user_id, "channel_delete", channel.guild.id
                )

                if threshold_exceeded:
                    logger.warning(f"⚠️ Mass channel deletion detected in {channel.guild.name}")
                    await self._perform_lockdown(
                        channel.guild,
                        user_id,
                        f"Mass channel deletion ({self.CHANNEL_DELETE_THRESHOLD}+ channels)"
                    )

                    # Update risk score
                    await self.db.update_risk_score(
                        channel.guild.id, user_id, 30.0,
                        "Mass channel deletion"
                    )
                break

        except Exception as e:
            logger.error(f"Channel deletion monitoring error: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Monitor channel creation."""
        try:
            config = await self.db.get_guild_config(channel.guild.id)

            if not config.get("antinuke_enabled"):
                return

            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                user_id = entry.user.id
                is_whitelisted = await self.db.is_user_whitelisted(channel.guild.id, user_id)

                if is_whitelisted or user_id == channel.guild.owner_id:
                    return

                threshold_exceeded = await self._check_thresholds(
                    user_id, "channel_create", channel.guild.id
                )

                if threshold_exceeded:
                    logger.warning(f"⚠️ Mass channel creation detected in {channel.guild.name}")
                    await self._perform_lockdown(
                        channel.guild, user_id,
                        f"Mass channel creation spree"
                    )
                    await self.db.update_risk_score(
                        channel.guild.id, user_id, 20.0,
                        "Mass channel creation"
                    )
                break

        except Exception as e:
            logger.error(f"Channel creation monitoring error: {e}")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Monitor role deletion."""
        try:
            config = await self.db.get_guild_config(role.guild.id)

            if not config.get("antinuke_enabled"):
                return

            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                user_id = entry.user.id
                is_whitelisted = await self.db.is_user_whitelisted(role.guild.id, user_id)

                if is_whitelisted or user_id == role.guild.owner_id:
                    return

                threshold_exceeded = await self._check_thresholds(
                    user_id, "role_delete", role.guild.id
                )

                if threshold_exceeded:
                    logger.warning(f"⚠️ Mass role deletion detected in {role.guild.name}")
                    await self._perform_lockdown(
                        role.guild, user_id,
                        f"Mass role deletion"
                    )
                    await self.db.update_risk_score(
                        role.guild.id, user_id, 35.0,
                        "Mass role deletion (critical)"
                    )
                break

        except Exception as e:
            logger.error(f"Role deletion monitoring error: {e}")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Monitor role creation."""
        try:
            config = await self.db.get_guild_config(role.guild.id)

            if not config.get("antinuke_enabled"):
                return

            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
                user_id = entry.user.id
                is_whitelisted = await self.db.is_user_whitelisted(role.guild.id, user_id)

                if is_whitelisted or user_id == role.guild.owner_id:
                    return

                threshold_exceeded = await self._check_thresholds(
                    user_id, "role_create", role.guild.id
                )

                if threshold_exceeded:
                    logger.warning(f"⚠️ Mass role creation detected")
                    await self._perform_lockdown(
                        role.guild, user_id,
                        "Mass role creation spree"
                    )
                break

        except Exception as e:
            logger.error(f"Role creation monitoring error: {e}")

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.TextChannel):
        """Monitor webhook creation/updates."""
        try:
            config = await self.db.get_guild_config(channel.guild.id)

            if not config.get("antinuke_enabled"):
                return

            async for entry in channel.guild.audit_logs(limit=3, action=discord.AuditLogAction.webhook_create):
                user_id = entry.user.id
                is_whitelisted = await self.db.is_user_whitelisted(channel.guild.id, user_id)

                if is_whitelisted or user_id == channel.guild.owner_id:
                    return

                threshold_exceeded = await self._check_thresholds(
                    user_id, "webhook_create", channel.guild.id
                )

                if threshold_exceeded:
                    logger.warning(f"⚠️ Suspicious webhook creation detected")
                    await self._perform_lockdown(
                        channel.guild, user_id,
                        "Suspicious webhook creation"
                    )
                break

        except Exception as e:
            logger.error(f"Webhook monitoring error: {e}")

    @tasks.loop(minutes=5)
    async def audit_monitor(self):
        """Monitor audit logs periodically."""
        try:
            # Clean old cache entries
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=1)

            for user_id in list(self.action_cache.keys()):
                self.action_cache[user_id] = [
                    a for a in self.action_cache[user_id]
                    if a["timestamp"] > cutoff
                ]

                if not self.action_cache[user_id]:
                    del self.action_cache[user_id]

        except Exception as e:
            logger.error(f"Audit monitor error: {e}")

    @audit_monitor.before_loop
    async def before_audit_monitor(self):
        """Wait for bot ready."""
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="antinuke_status", description="Check anti-nuke status")
    async def antinuke_status(self, ctx: commands.Context):
        """Check current anti-nuke status."""
        try:
            config = await self.db.get_guild_config(ctx.guild.id)

            embed = discord.Embed(
                title="🛡️ Anti-Nuke Status",
                color=discord.Color.green() if config.get("antinuke_enabled") else discord.Color.red(),
            )
            embed.add_field(
                name="Status",
                value="✅ Enabled" if config.get("antinuke_enabled") else "❌ Disabled",
                inline=False
            )
            embed.add_field(
                name="Lockdown Mode",
                value="🔒 Active" if config.get("lockdown_mode") else "🔓 Off",
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    # Note: unlock command is defined as a global command in main.py


async def setup(bot: commands.Bot):
    """Setup cog."""
    await bot.add_cog(AntiNuke(bot))
