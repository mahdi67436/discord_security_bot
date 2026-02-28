"""
Moderation, Anti-Bot, and Advanced Content Filtering Cog
Handles bad word filtering, link detection, and malicious bot protection.
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from database.db import get_db
from utils.filters import TextFilter, MessageFilter, SpamFilter
from utils.permissions import PermissionValidator
from utils.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class Moderation(commands.Cog):
    """Moderation and content filtering."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = None
        self.spam_filter = SpamFilter(max_messages=5, time_window=5)

    async def cog_load(self):
        """Load cog."""
        self.db = get_db()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle message content filtering."""
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return

        try:
            config = await self.db.get_guild_config(message.guild.id)

            # Get custom badwords
            custom_badwords = await self.db.get_custom_badwords(message.guild.id)

            # Check message
            should_delete, reason = await MessageFilter.check_message(
                message.content,
                message.guild.id,
                custom_badwords
            )

            if not should_delete:
                return

            # Bad content detected
            logger.warning(f"Deleted message from {message.author}: {reason}")

            # Delete message
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            # Send warning
            try:
                embed = discord.Embed(
                    title="⚠️ Message Deleted",
                    description=f"Your message was removed: **{reason}**",
                    color=discord.Color.orange(),
                )
                embed.set_footer(text=f"This is automatic moderation")

                dm = await message.author.create_dm()
                await dm.send(embed=embed)
            except discord.Forbidden:
                pass

            # Add warning
            warning_count = await self.db.add_warning(
                message.guild.id,
                message.author.id,
                reason,
                self.bot.user.id
            )

            # Update risk score
            risk_delta = RiskEngine.calculate_infraction_score("badword_violation")
            await self.db.update_risk_score(
                message.guild.id,
                message.author.id,
                risk_delta,
                reason
            )

            # Check if reached warning threshold
            if warning_count >= 3:
                logger.warning(f"Timing out {message.author} after {warning_count} warnings")

                try:
                    await message.author.timeout(
                        timedelta(hours=24),
                        reason=f"[AUTO] {warning_count} content violations"
                    )
                except discord.Forbidden:
                    pass

            # Log to security channel
            log_channel_id = config.get("log_channel_id")
            if log_channel_id:
                try:
                    log_channel = message.guild.get_channel(log_channel_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="🔴 Content Violation",
                            description=f"**User**: {message.author.mention}\n**Reason**: {reason}",
                            color=discord.Color.red(),
                        )
                        embed.add_field(name="Warning Count", value=warning_count, inline=True)
                        embed.add_field(name="Content", value=f"```{message.content[:100]}```", inline=False)
                        embed.timestamp = datetime.now(timezone.utc)

                        await log_channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to send moderation log: {e}")

        except Exception as e:
            logger.error(f"Message filtering error: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Monitor member role changes."""
        try:
            config = await self.db.get_guild_config(after.guild.id)

            if not config.get("antinuke_enabled"):
                return

            # Check if roles were changed
            if before.roles == after.roles:
                return

            # Get role change details
            added_roles = [r for r in after.roles if r not in before.roles]
            removed_roles = [r for r in before.roles if r not in after.roles]

            # Check for suspicious role additions
            for role in added_roles:
                dangerous_perms = PermissionValidator.get_dangerous_permission_names(role.permissions)
                if dangerous_perms:
                    logger.warning(f"⚠️ Dangerous role added to {after}: {dangerous_perms}")

                    # Update risk
                    await self.db.update_risk_score(
                        after.guild.id,
                        after.id,
                        RiskEngine.calculate_infraction_score("rapid_escalation"),
                        f"Granted dangerous roles: {', '.join(dangerous_perms)}"
                    )

        except Exception as e:
            logger.error(f"Member update monitoring error: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Check joining bots."""
        try:
            config = await self.db.get_guild_config(member.guild.id)

            if not config.get("antibot_enabled") or not member.bot:
                return

            # Check if bot is whitelisted
            is_whitelisted = await self.db.is_bot_whitelisted(member.guild.id, member.id)
            if is_whitelisted:
                logger.info(f"✅ Whitelisted bot joined: {member}")
                return

            # Check bot permissions in join event
            # (Limited data available, additional checks in commands)
            logger.info(f"🤖 Bot joined: {member}")

        except Exception as e:
            logger.error(f"Bot join monitoring error: {e}")

    # Commands for moderation

    @commands.hybrid_command(name="warn", description="Warn a user")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        """Warn a user."""
        try:
            if member == ctx.author:
                await ctx.send("❌ You cannot warn yourself.")
                return

            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("❌ Cannot warn someone with equal or higher role.")
                return

            # Add warning
            warning_count = await self.db.add_warning(
                ctx.guild.id,
                member.id,
                reason,
                ctx.author.id
            )

            # Update risk
            await self.db.update_risk_score(
                ctx.guild.id,
                member.id,
                5.0,
                f"Manual warn: {reason}"
            )

            embed = discord.Embed(
                title="⚠️ Warning Issued",
                description=f"**User**: {member.mention}\n**Reason**: {reason}",
                color=discord.Color.orange(),
            )
            embed.add_field(name="Total Warnings", value=warning_count, inline=True)
            embed.timestamp = datetime.now(timezone.utc)

            await ctx.send(embed=embed)

            # Try to notify user
            try:
                await member.send(f"⚠️ You were warned in {ctx.guild.name} for: {reason}")
            except discord.Forbidden:
                pass

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="clearwarn", description="Clear user warnings")
    @commands.has_permissions(administrator=True)
    async def clear_warn(self, ctx: commands.Context, member: discord.Member):
        """Clear warnings for a user."""
        try:
            await self.db.clear_warnings(ctx.guild.id, member.id)

            embed = discord.Embed(
                title="✅ Warnings Cleared",
                description=f"Cleared all warnings for {member.mention}",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="addcustomword", description="Add custom badword")
    @commands.has_permissions(administrator=True)
    async def add_custom_word(self, ctx: commands.Context, word: str, severity: str = "medium"):
        """Add custom badword to filter."""
        try:
            if severity not in ["low", "medium", "high"]:
                await ctx.send("❌ Severity must be: low, medium, or high")
                return

            await self.db.add_custom_badword(ctx.guild.id, word, severity, ctx.author.id)

            embed = discord.Embed(
                title="➕ Custom Word Added",
                description=f"Added `{word}` to filter (Severity: {severity})",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="removecustomword", description="Remove custom badword")
    @commands.has_permissions(administrator=True)
    async def remove_custom_word(self, ctx: commands.Context, word: str):
        """Remove custom badword."""
        try:
            removed = await self.db.remove_custom_badword(ctx.guild.id, word)

            if not removed:
                await ctx.send(f"❌ Word `{word}` not found in custom filter.")
                return

            embed = discord.Embed(
                title="➖ Custom Word Removed",
                description=f"Removed `{word}` from filter",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="getrisk", description="Check user risk score")
    @commands.has_permissions(kick_members=True)
    async def get_risk(self, ctx: commands.Context, member: discord.Member):
        """Check user risk score."""
        try:
            risk_data = await self.db.get_risk_score(ctx.guild.id, member.id)
            risk_score = risk_data.get("risk_score", 0.0)
            warning_count = risk_data.get("warning_count", 0)

            risk_level = RiskEngine.get_risk_level(risk_score)
            action = RiskEngine.get_recommended_action(risk_score)

            embed = discord.Embed(
                title="📊 User Risk Assessment",
                description=f"**User**: {member.mention}",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Risk Score", value=f"{risk_score:.1f}/100", inline=True)
            embed.add_field(name="Risk Level", value=risk_level, inline=True)
            embed.add_field(name="Warnings", value=warning_count, inline=True)
            embed.add_field(name="Recommended Action", value=action, inline=False)
            embed.timestamp = datetime.now(timezone.utc)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")


async def setup(bot: commands.Bot):
    """Setup cog."""
    await bot.add_cog(Moderation(bot))
