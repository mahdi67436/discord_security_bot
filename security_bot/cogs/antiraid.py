"""
Advanced Anti-Raid Cog - Detects mass joins and raid attempts.
Monitors account age, patterns, and suspicious behavior.
"""

import discord
from discord.ext import commands, tasks
import logging
from typing import Dict, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from database.db import get_db
from utils.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class AntiRaid(commands.Cog):
    """Anti-raid protection system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = None
        # Track joins per guild
        self.join_tracker: Dict[int, List[int]] = defaultdict(list)
        # Track suspicious accounts
        self.suspicious_users: Dict[int, List[int]] = defaultdict(list)
        self.raid_monitor.start()

    async def cog_load(self):
        """Load cog."""
        self.db = get_db()

    # Raid detection thresholds
    JOINS_PER_MINUTE = 5  # 5 joins in 1 minute = suspicious
    MAX_YOUNG_ACCOUNTS = 10  # 10+ accounts <7 days old
    TIME_WINDOW = 60  # seconds
    YOUNG_ACCOUNT_DAYS = 7

    async def _analyze_member(self, member: discord.Member) -> Dict:
        """Analyze member for suspicious patterns."""
        analysis = {
            "is_suspicious": False,
            "reasons": [],
            "risk_score": 0.0,
        }

        # Check account age
        age_risk = RiskEngine.analyze_account_age(member.created_at)
        if age_risk > 10:
            analysis["is_suspicious"] = True
            analysis["reasons"].append(f"Brand new account ({age_risk}% risk)")
            analysis["risk_score"] += age_risk

        # Check join date
        join_age_risk = RiskEngine.analyze_account_age(member.joined_at)
        if join_age_risk > 5:
            analysis["reasons"].append("Joined recently")
            analysis["risk_score"] += join_age_risk / 2

        # Check for avatar
        if not member.avatar:
            analysis["reasons"].append("No avatar set")
            analysis["risk_score"] += 5.0

        # Check username patterns
        suspicious_patterns = [
            r"discord.*bot", r"n[i1]gg", r"raid", r"spam",
        ]
        import re
        for pattern in suspicious_patterns:
            if re.search(pattern, member.name.lower()):
                analysis["is_suspicious"] = True
                analysis["reasons"].append(f"Suspicious username pattern")
                analysis["risk_score"] += 15.0
                break

        # Check bot indicator
        if member.bot:
            analysis["is_suspicious"] = True
            analysis["reasons"].append("Member is a bot")
            analysis["risk_score"] += 5.0

        return analysis

    async def _perform_raid_lockdown(self, guild: discord.Guild, reason: str):
        """Activate raid protection lockdown."""
        try:
            logger.warning(f"🚨 RAID DETECTED in {guild.name}: {reason}")

            config = await self.db.get_guild_config(guild.id)
            log_channel_id = config.get("log_channel_id")

            # Enable verification level
            try:
                await guild.edit(verification_level=discord.VerificationLevel.high)
            except discord.Forbidden:
                pass

            # Lock all channels
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(
                        guild.default_role,
                        send_messages=False,
                        add_reactions=False,
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass

            # Update database
            await self.db.update_raid_detection(
                guild.id, 
                join_count=len(self.join_tracker[guild.id]),
                suspicious_accounts=len(self.suspicious_users[guild.id]),
                lockdown_enabled=True
            )

            # Log to security channel
            if log_channel_id:
                try:
                    log_channel = guild.get_channel(log_channel_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="🚨 RAID DETECTED",
                            description=reason,
                            color=discord.Color.red(),
                        )
                        embed.add_field(
                            name="Suspicious Joins",
                            value=len(self.join_tracker[guild.id]),
                            inline=True
                        )
                        embed.add_field(
                            name="Young Accounts",
                            value=len(self.suspicious_users[guild.id]),
                            inline=True
                        )
                        embed.timestamp = datetime.now(timezone.utc)
                        await log_channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to send raid log: {e}")

            # Notify owner
            try:
                embed = discord.Embed(
                    title="🚨 RAID ALERT",
                    description=f"Your server **{guild.name}** is under raid attack!",
                    color=discord.Color.red(),
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Action", value="Server locked and verification enabled", inline=False)
                embed.add_field(name="Next Steps", value="Use `!raidstatus` to check and `!unlock` when ready", inline=False)

                await guild.owner.send(embed=embed)
            except discord.Forbidden:
                pass

        except Exception as e:
            logger.error(f"Raid lockdown error: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Monitor member joins for raids."""
        try:
            config = await self.db.get_guild_config(member.guild.id)

            if not config.get("antiraid_enabled"):
                return

            # Analyze member
            analysis = await self._analyze_member(member)

            # Track all joins in time window
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(seconds=self.TIME_WINDOW)

            # Clean old joins
            self.join_tracker[member.guild.id] = [
                ts for ts in self.join_tracker[member.guild.id]
                if ts > cutoff.timestamp()
            ]

            # Add current join
            self.join_tracker[member.guild.id].append(now.timestamp())

            join_count = len(self.join_tracker[member.guild.id])

            # Log joins
            logger.info(f"Member joined {member.guild.name}: {member} ({join_count} joins in {self.TIME_WINDOW}s)")

            # Check join rate
            if join_count >= self.JOINS_PER_MINUTE:
                await self._perform_raid_lockdown(
                    member.guild,
                    f"Mass joins detected: {join_count} members in {self.TIME_WINDOW} seconds"
                )
                return

            # Track suspicious members
            if analysis["is_suspicious"]:
                self.suspicious_users[member.guild.id].append(member.id)

                # Auto-timeout suspicious accounts
                try:
                    timeout_duration = timedelta(hours=24)
                    await member.timeout(timeout_duration, reason="[AUTO] Suspicious account in raid")
                    logger.warning(f"⏱️ Timed out suspicious member: {member}")
                except discord.Forbidden:
                    pass

                # Update risk score
                await self.db.update_risk_score(
                    member.guild.id,
                    member.id,
                    analysis["risk_score"],
                    f"Raid detection: {', '.join(analysis['reasons'])}"
                )

            # Check if multiple suspicious accounts
            if len(self.suspicious_users[member.guild.id]) >= self.MAX_YOUNG_ACCOUNTS:
                await self._perform_raid_lockdown(
                    member.guild,
                    f"Multiple suspicious accounts detected: {len(self.suspicious_users[member.guild.id])}"
                )

        except Exception as e:
            logger.error(f"Member join monitoring error: {e}")

    @tasks.loop(minutes=5)
    async def raid_monitor(self):
        """Periodic raid monitoring and cleanup."""
        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=1)

            # Clean old tracking data
            for guild_id in list(self.join_tracker.keys()):
                self.join_tracker[guild_id] = [
                    ts for ts in self.join_tracker[guild_id]
                    if ts > cutoff.timestamp()
                ]

                if not self.join_tracker[guild_id]:
                    del self.join_tracker[guild_id]

            for guild_id in list(self.suspicious_users.keys()):
                self.suspicious_users[guild_id] = [
                    uid for uid in self.suspicious_users[guild_id]
                ]

                if not self.suspicious_users[guild_id]:
                    del self.suspicious_users[guild_id]

        except Exception as e:
            logger.error(f"Raid monitor cleanup error: {e}")

    @raid_monitor.before_loop
    async def before_raid_monitor(self):
        """Wait for bot ready."""
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="raidstatus", description="Check raid status")
    async def raid_status(self, ctx: commands.Context):
        """Check raid status."""
        try:
            raid_status = await self.db.get_raid_status(ctx.guild.id)

            embed = discord.Embed(
                title="📊 Raid Status",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Suspicious Joins",
                value=len(self.join_tracker.get(ctx.guild.id, [])),
                inline=True
            )
            embed.add_field(
                name="Young Accounts",
                value=len(self.suspicious_users.get(ctx.guild.id, [])),
                inline=True
            )
            embed.add_field(
                name="Lockdown Active",
                value="🔒 Yes" if raid_status.get("lockdown_enabled") else "🟢 No",
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="clearsuspicious", description="Clear suspicious users list")
    @commands.has_permissions(administrator=True)
    async def clear_suspicious(self, ctx: commands.Context):
        """Clear suspicious users tracking."""
        try:
            self.suspicious_users[ctx.guild.id] = []
            self.join_tracker[ctx.guild.id] = []

            await ctx.send("✅ Suspicious users list cleared.")
            logger.info(f"Suspicious users cleared in {ctx.guild.name}")

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")


async def setup(bot: commands.Bot):
    """Setup cog."""
    await bot.add_cog(AntiRaid(bot))
