"""
Permission validation utilities for security enforcement.
"""

import discord
from typing import List, Tuple
from discord.ext import commands


class PermissionValidator:
    """Validates and manages permission-related security checks."""

    DANGEROUS_PERMISSIONS = [
        discord.Permissions.administrator,
        discord.Permissions.manage_guild,
        discord.Permissions.manage_roles,
        discord.Permissions.manage_channels,
        discord.Permissions.manage_webhooks,
        discord.Permissions.ban_members,
        discord.Permissions.kick_members,
        discord.Permissions.manage_messages,
        discord.Permissions.mute_members,
        discord.Permissions.deafen_members,
        discord.Permissions.move_members,
    ]

    @staticmethod
    def has_dangerous_permissions(perms: discord.Permissions) -> bool:
        """Check if permissions contain dangerous flags."""
        permission_value = perms.value
        for dangerous_perm in PermissionValidator.DANGEROUS_PERMISSIONS:
            if permission_value & dangerous_perm.flag:
                return True
        return False

    @staticmethod
    def get_dangerous_permission_names(perms: discord.Permissions) -> List[str]:
        """Get list of dangerous permission names."""
        dangerous = []
        perm_dict = dict(perms)
        
        dangerous_perm_names = {
            'administrator': 'Administrator',
            'manage_guild': 'Manage Server',
            'manage_roles': 'Manage Roles',
            'manage_channels': 'Manage Channels',
            'manage_webhooks': 'Manage Webhooks',
            'ban_members': 'Ban Members',
            'kick_members': 'Kick Members',
            'manage_messages': 'Manage Messages',
            'mute_members': 'Mute Members',
            'deafen_members': 'Deafen Members',
            'move_members': 'Move Members',
        }
        
        for perm, readable in dangerous_perm_names.items():
            if perm_dict.get(perm):
                dangerous.append(readable)
        
        return dangerous

    @staticmethod
    def is_admin_or_moderator(member: discord.Member, admin_role: discord.Role = None) -> bool:
        """Check if member is admin or mod."""
        if member.guild_permissions.administrator:
            return True
        if admin_role and admin_role in member.roles:
            return True
        return False

    @staticmethod
    def can_manage_perms(actor: discord.Member, target: discord.Member) -> bool:
        """Check if actor can manage target's roles."""
        if actor.guild_permissions.administrator:
            return True
        if actor.top_role <= target.top_role:
            return False
        return actor.guild_permissions.manage_roles

    @staticmethod
    def strip_dangerous_perms(perms: discord.Permissions) -> discord.Permissions:
        """Create a new permissions object with dangerous perms removed."""
        new_perms = discord.Permissions(perms.value)
        for dangerous_perm in PermissionValidator.DANGEROUS_PERMISSIONS:
            if new_perms.value & dangerous_perm.flag:
                new_perms.value &= ~dangerous_perm.flag
        return new_perms

    @staticmethod
    def validate_invite(invite_code: str) -> Tuple[bool, str]:
        """Validate if string looks like Discord invite."""
        # Basic Discord invite patterns
        invite_patterns = [
            r'^[a-zA-Z0-9\-_]{2,}$',  # Generic invite code
        ]
        
        if any(len(invite_code) > 1 and len(invite_code) < 20 for _ in [None]):
            return True, "Detected potential invite code"
        
        return False, "Not an invite"

    @staticmethod
    def require_permission(permission: discord.Permissions):
        """Decorator to require specific permission."""
        async def predicate(ctx):
            if not ctx.author.guild_permissions >= permission:
                raise commands.MissingPermissions([permission])
            return True
        return commands.check(predicate)
