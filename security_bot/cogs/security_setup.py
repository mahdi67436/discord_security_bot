"""
Automatic Security Setup Cog
Automates security configuration with the !setup_security command.
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone

from database.db import get_db

logger = logging.getLogger(__name__)


class SecuritySetup(commands.Cog):
    """Automatic security configuration."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = None

    async def cog_load(self):
        """Load cog."""
        self.db = get_db()

    @commands.hybrid_command(name="setup_security", description="Automatic security setup")
    @commands.has_permissions(administrator=True)
    async def setup_security(self, ctx: commands.Context):
        """Setup complete security system automatically."""
        try:
            embed = discord.Embed(
                title="🔧 Setting Up Security...",
                description="Configuring your server security. This may take a minute.",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)

            # Step 1: Create security role
            logger.info(f"[{ctx.guild.name}] Creating security role...")
            try:
                security_role = await ctx.guild.create_role(
                    name="🛡️ Security Bot",
                    color=discord.Color.red(),
                    permissions=discord.Permissions(
                        administrator=False,
                        manage_channels=True,
                        manage_roles=True,
                        manage_guild=True,
                        moderate_members=True,
                        ban_members=True,
                        kick_members=True,
                    ),
                    reason="[AUTO-SETUP] Security management role",
                )
                logger.info(f"✓ Security role created: {security_role.name}")
            except discord.Forbidden:
                await ctx.send("❌ Missing permissions to create roles")
                return

            # Step 2: Create log channel
            logger.info(f"[{ctx.guild.name}] Creating log channel...")
            try:
                log_channel = await ctx.guild.create_text_channel(
                    name="🔒-security-logs",
                    position=0,
                    topic="Security Events & Audit Logs",
                    reason="[AUTO-SETUP] Security logging",
                )

                # Set permissions
                await log_channel.set_permissions(
                    ctx.guild.default_role,
                    read_messages=False,
                )
                await log_channel.set_permissions(
                    security_role,
                    read_messages=True,
                    send_messages=True,
                )

                logger.info(f"✓ Log channel created: {log_channel.name}")

                # Send welcome message
                embed = discord.Embed(
                    title="🛡️ Security System Activated",
                    description="This channel logs all security events and threats.",
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="Active Protections",
                    value=(
                        "✓ Anti-Nuke System\n"
                        "✓ Anti-Raid Protection\n"
                        "✓ Content Filtering\n"
                        "✓ Malicious Link Detection\n"
                        "✓ Bad Word Filter (Multi-Language)\n"
                        "✓ Automatic Backups\n"
                        "✓ Permission Lockdown\n"
                        "✓ Risk Scoring Engine"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="Useful Commands",
                    value=(
                        "`/security-status` - System status\n"
                        "`/warn` - Warn a user\n"
                        "`/getrisk` - Check user risk score\n"
                        "`/createbackup` - Manual backup\n"
                        "`/restore` - Restore from backup\n"
                        "`/lockdown` - Emergency lockdown\n"
                        "`/unlock` - Exit lockdown"
                    ),
                    inline=False
                )
                embed.timestamp = datetime.now(timezone.utc)

                await log_channel.send(embed=embed)

            except discord.Forbidden:
                await ctx.send("❌ Missing permissions to create channels")
                return

            # Step 3: Store configuration
            logger.info(f"[{ctx.guild.name}] Storing configuration...")
            await self.db.update_guild_config(
                ctx.guild.id,
                antinuke_enabled=True,
                antiraid_enabled=True,
                antibot_enabled=True,
                antibadword_enabled=True,
                antilink_enabled=True,
                security_role_id=security_role.id,
                log_channel_id=log_channel.id,
                lockdown_mode=False,
            )

            # Step 4: Create verification channel
            logger.info(f"[{ctx.guild.name}] Creating verification setup...")
            try:
                verify_channel = await ctx.guild.create_text_channel(
                    name="📋-verification",
                    position=0,
                    topic="Member verification and information",
                    reason="[AUTO-SETUP] Verification channel",
                )

                embed = discord.Embed(
                    title="👋 Welcome to Our Server!",
                    description="Please read the rules and verify yourself.",
                    color=discord.Color.blue(),
                )
                embed.add_field(name="Security Features", value="This server is protected by military-grade security", inline=False)

                await verify_channel.send(embed=embed)

            except discord.Forbidden:
                logger.warning("Could not create verification channel")

            # Send completion report
            embed = discord.Embed(
                title="✅ Security Setup Complete!",
                description="Your server is now protected",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Created",
                value=f"• Role: {security_role.mention}\n• Log Channel: {log_channel.mention}",
                inline=False
            )
            embed.add_field(
                name="Enabled Systems",
                value=(
                    "✓ Anti-Nuke Protection\n"
                    "✓ Raid Detection\n"
                    "✓ Content Filtering\n"
                    "✓ Bot Protection"
                ),
                inline=False
            )
            embed.add_field(
                name="Next Steps",
                value=(
                    "1. Review security settings\n"
                    "2. Add trusted moderators\n"
                    "3. Use `/addwhitelist` for trusted users\n"
                    "4. Check `!security-report` for details"
                ),
                inline=False
            )
            embed.timestamp = datetime.utcnow()

            await ctx.send(embed=embed)
            logger.info(f"✅ Security setup completed for {ctx.guild.name}")

        except Exception as e:
            logger.error(f"Setup error: {e}")
            await ctx.send(f"❌ Setup failed: {e}")

    @commands.hybrid_command(name="security_report", description="Detailed security report")
    @commands.has_permissions(administrator=True)
    async def security_report(self, ctx: commands.Context):
        """Generate detailed security report."""
        try:
            config = await self.db.get_guild_config(ctx.guild.id)

            embed = discord.Embed(
                title="📊 Security Report",
                description=f"Report for **{ctx.guild.name}**",
                color=discord.Color.blue(),
            )

            # System status
            systems_status = (
                f"{'✅' if config.get('antinuke_enabled') else '❌'} Anti-Nuke\n"
                f"{'✅' if config.get('antiraid_enabled') else '❌'} Anti-Raid\n"
                f"{'✅' if config.get('antibot_enabled') else '❌'} Bot Protection\n"
                f"{'✅' if config.get('antibadword_enabled') else '❌'} Content Filter\n"
                f"{'✅' if config.get('antilink_enabled') else '❌'} Link Detection"
            )

            embed.add_field(name="Active Systems", value=systems_status, inline=True)

            # Lockdown status
            lockdown_status = "🔒 Active" if config.get("lockdown_mode") else "🟢 Normal"
            embed.add_field(name="Lockdown Mode", value=lockdown_status, inline=True)

            # Server stats
            embed.add_field(
                name="📈 Statistics",
                value=(
                    f"Members: {ctx.guild.member_count}\n"
                    f"Roles: {len(ctx.guild.roles)}\n"
                    f"Channels: {len(ctx.guild.channels)}\n"
                    f"Created: {ctx.guild.created_at.strftime('%Y-%m-%d')}"
                ),
                inline=False
            )

            # Recommendations
            recommendations = []
            if ctx.guild.member_count < 50:
                recommendations.append("• Consider enabling higher verification levels for safety")
            if len(ctx.guild.roles) > 20:
                recommendations.append("• Many roles detected - ensure role hierarchy is correct")

            if recommendations:
                embed.add_field(
                    name="💡 Recommendations",
                    value="\n".join(recommendations),
                    inline=False
                )

            embed.timestamp = datetime.now(timezone.utc)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="toggle_system", description="Toggle security system")
    @commands.has_permissions(administrator=True)
    async def toggle_system(
        self, ctx: commands.Context,
        system: str,
        enabled: bool
    ):
        """Toggle security systems."""
        try:
            config = await self.db.get_guild_config(ctx.guild.id)

            system_mapping = {
                "antinuke": "antinuke_enabled",
                "antiraid": "antiraid_enabled",
                "antibot": "antibot_enabled",
                "badword": "antibadword_enabled",
                "antilink": "antilink_enabled",
            }

            if system.lower() not in system_mapping:
                await ctx.send(f"❌ Unknown system. Available: {', '.join(system_mapping.keys())}")
                return

            field = system_mapping[system.lower()]

            await self.db.update_guild_config(ctx.guild.id, **{field: enabled})

            status = "✅ Enabled" if enabled else "❌ Disabled"
            embed = discord.Embed(
                title=f"System Toggle",
                description=f"{system.upper()} is now {status}",
                color=discord.Color.green() if enabled else discord.Color.red(),
            )

            await ctx.send(embed=embed)
            logger.info(f"System toggle: {system} = {enabled} in {ctx.guild.name}")

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="addwhitelist", description="Add user to whitelist")
    @commands.has_permissions(administrator=True)
    async def add_whitelist(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Admin whitelist"):
        """Add user to security whitelist."""
        try:
            await self.db.add_whitelist_user(
                ctx.guild.id,
                member.id,
                reason,
                ctx.author.id
            )

            embed = discord.Embed(
                title="✅ User Whitelisted",
                description=f"{member.mention} added to security whitelist",
                color=discord.Color.green(),
            )
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)
            logger.info(f"Whitelisted {member} in {ctx.guild.name}")

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.hybrid_command(name="removewhitelist", description="Remove user from whitelist")
    @commands.has_permissions(administrator=True)
    async def remove_whitelist(self, ctx: commands.Context, member: discord.Member):
        """Remove user from whitelist."""
        try:
            removed = await self.db.remove_whitelist_user(ctx.guild.id, member.id)

            if not removed:
                await ctx.send(f"❌ {member} is not on the whitelist.")
                return

            embed = discord.Embed(
                title="❌ User Un-Whitelisted",
                description=f"{member.mention} removed from security whitelist",
                color=discord.Color.orange(),
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")


async def setup(bot: commands.Bot):
    """Setup cog."""
    await bot.add_cog(SecuritySetup(bot))
