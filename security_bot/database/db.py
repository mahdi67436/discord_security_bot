"""
Database initialization and management module for the security bot.
Supports both SQLite (dev) and PostgreSQL (production).
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import os

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages all database operations with dev/prod flexibility."""

    def __init__(self, db_type: str = "sqlite", db_path: str = "security_bot.db"):
        """
        Initialize database manager.
        
        Args:
            db_type: "sqlite" or "postgresql"
            db_path: Path to SQLite database or connection string
        """
        self.db_type = db_type
        self.db_path = db_path
        self.connection = None
        self.cursor = None

    async def init_db(self):
        """Initialize database connection and create tables."""
        try:
            if self.db_type == "sqlite":
                # Use row factory to return rows as dictionaries
                self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
                self.connection.row_factory = dict_factory
                self.cursor = self.connection.cursor()
            else:
                logger.error("PostgreSQL not yet implemented in this environment")
                raise NotImplementedError("Use SQLite for now")

            await self._create_tables()
            logger.info("✓ Database initialized successfully")
        except Exception as e:
            logger.error(f"✗ Database initialization failed: {e}")
            raise

    async def _create_tables(self):
        """Create all required database tables."""
        tables = {
            "guild_configs": """
                CREATE TABLE IF NOT EXISTS guild_configs (
                    guild_id INTEGER PRIMARY KEY,
                    antinuke_enabled BOOLEAN DEFAULT 1,
                    antiraid_enabled BOOLEAN DEFAULT 1,
                    antibot_enabled BOOLEAN DEFAULT 1,
                    antibadword_enabled BOOLEAN DEFAULT 1,
                    antilink_enabled BOOLEAN DEFAULT 1,
                    security_role_id INTEGER,
                    log_channel_id INTEGER,
                    lockdown_mode BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "user_warnings": """
                CREATE TABLE IF NOT EXISTS user_warnings (
                    warning_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    moderator_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """,
            "user_risk_scores": """
                CREATE TABLE IF NOT EXISTS user_risk_scores (
                    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    risk_score REAL DEFAULT 0.0,
                    warning_count INTEGER DEFAULT 0,
                    last_infraction TIMESTAMP,
                    flag_reason TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """,
            "whitelisted_users": """
                CREATE TABLE IF NOT EXISTS whitelisted_users (
                    whitelist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    reason TEXT,
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """,
            "whitelisted_bots": """
                CREATE TABLE IF NOT EXISTS whitelisted_bots (
                    bot_whitelist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    bot_id INTEGER NOT NULL,
                    reason TEXT,
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """,
            "whitelisted_links": """
                CREATE TABLE IF NOT EXISTS whitelisted_links (
                    link_whitelist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    domain TEXT NOT NULL,
                    reason TEXT,
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """,
            "custom_badwords": """
                CREATE TABLE IF NOT EXISTS custom_badwords (
                    badword_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    severity TEXT DEFAULT 'medium',
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """,
            "audit_log_cache": """
                CREATE TABLE IF NOT EXISTS audit_log_cache (
                    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    user_id INTEGER,
                    target_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """,
            "raid_detection": """
                CREATE TABLE IF NOT EXISTS raid_detection (
                    raid_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    join_count INTEGER DEFAULT 0,
                    suspicious_accounts INTEGER DEFAULT 0,
                    lockdown_enabled BOOLEAN DEFAULT 0,
                    detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """,
            "backup_metadata": """
                CREATE TABLE IF NOT EXISTS backup_metadata (
                    backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    backup_name TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id)
                )
            """
        }

        for table_name, create_sql in tables.items():
            try:
                self.cursor.execute(create_sql)
                self.connection.commit()
                logger.info(f"✓ Table '{table_name}' ready")
            except sqlite3.OperationalError as e:
                logger.info(f"→ Table '{table_name}' already exists")

    async def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("✓ Database connection closed")

    # Guild Config Operations
    async def get_guild_config(self, guild_id: int) -> Optional[Dict]:
        """Get guild configuration."""
        self.cursor.execute("SELECT * FROM guild_configs WHERE guild_id = ?", (guild_id,))
        result = self.cursor.fetchone()
        if not result:
            return await self.create_guild_config(guild_id)
        # result may already be a dict, sqlite3.Row, or tuple
        if isinstance(result, dict):
            return result
        if isinstance(result, sqlite3.Row):
            return dict(result)
        # fallback: build dict using description
        cols = [col[0] for col in self.cursor.description]
        return dict(zip(cols, result))

    async def create_guild_config(self, guild_id: int) -> Dict:
        """Create new guild configuration."""
        self.cursor.execute(
            "INSERT INTO guild_configs (guild_id) VALUES (?)",
            (guild_id,)
        )
        self.connection.commit()
        return await self.get_guild_config(guild_id)

    async def update_guild_config(self, guild_id: int, **kwargs) -> bool:
        """Update guild configuration."""
        allowed_fields = [
            "antinuke_enabled", "antiraid_enabled", "antibot_enabled",
            "antibadword_enabled", "antilink_enabled", "security_role_id",
            "log_channel_id", "lockdown_mode"
        ]
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [guild_id]

        self.cursor.execute(f"UPDATE guild_configs SET {set_clause} WHERE guild_id = ?", values)
        self.connection.commit()
        return True

    # Warning Operations
    async def add_warning(self, guild_id: int, user_id: int, reason: str, moderator_id: int) -> int:
        """Add warning to user."""
        self.cursor.execute(
            "INSERT INTO user_warnings (guild_id, user_id, reason, moderator_id) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, moderator_id)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    async def get_user_warnings(self, guild_id: int, user_id: int) -> int:
        """Get user warning count."""
        self.cursor.execute(
            "SELECT COUNT(*) FROM user_warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        return self.cursor.fetchone()[0]

    async def clear_warnings(self, guild_id: int, user_id: int) -> bool:
        """Clear user warnings."""
        self.cursor.execute(
            "DELETE FROM user_warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        self.connection.commit()
        return True

    # Risk Score Operations
    async def get_risk_score(self, guild_id: int, user_id: int) -> Dict:
        """Get user risk score."""
        self.cursor.execute(
            "SELECT * FROM user_risk_scores WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        result = self.cursor.fetchone()
        return dict(result) if result else {"risk_score": 0.0, "warning_count": 0}

    async def update_risk_score(self, guild_id: int, user_id: int, delta: float,
                               reason: str = None) -> float:
        """Update user risk score."""
        current = await self.get_risk_score(guild_id, user_id)
        new_score = min(100.0, max(0.0, current.get("risk_score", 0) + delta))

        self.cursor.execute(
            """INSERT INTO user_risk_scores (guild_id, user_id, risk_score, flag_reason, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(guild_id, user_id) DO UPDATE SET 
               risk_score = ?, flag_reason = ?, updated_at = ?""",
            (guild_id, user_id, new_score, reason, datetime.now(timezone.utc).isoformat(),
             new_score, reason, datetime.now(timezone.utc).isoformat())
        )
        self.connection.commit()
        return new_score

    # Whitelist Operations
    async def is_user_whitelisted(self, guild_id: int, user_id: int) -> bool:
        """Check if user is whitelisted."""
        self.cursor.execute(
            "SELECT 1 FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        return self.cursor.fetchone() is not None

    async def is_bot_whitelisted(self, guild_id: int, bot_id: int) -> bool:
        """Check if bot is whitelisted."""
        self.cursor.execute(
            "SELECT 1 FROM whitelisted_bots WHERE guild_id = ? AND bot_id = ?",
            (guild_id, bot_id)
        )
        return self.cursor.fetchone() is not None

    async def is_domain_whitelisted(self, guild_id: int, domain: str) -> bool:
        """Check if domain is whitelisted."""
        self.cursor.execute(
            "SELECT 1 FROM whitelisted_links WHERE guild_id = ? AND domain = ?",
            (guild_id, domain)
        )
        return self.cursor.fetchone() is not None

    async def add_whitelist_user(self, guild_id: int, user_id: int, reason: str, added_by: int):
        """Add user to whitelist."""
        self.cursor.execute(
            "INSERT INTO whitelisted_users (guild_id, user_id, reason, added_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, added_by)
        )
        self.connection.commit()

    async def remove_whitelist_user(self, guild_id: int, user_id: int) -> bool:
        """Remove user from whitelist."""
        self.cursor.execute(
            "DELETE FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        self.connection.commit()
        return self.cursor.rowcount > 0

    # Custom Badword Operations
    async def add_custom_badword(self, guild_id: int, word: str, severity: str = "medium", added_by: int = None):
        """Add custom badword to guild."""
        self.cursor.execute(
            "INSERT INTO custom_badwords (guild_id, word, severity, added_by) VALUES (?, ?, ?, ?)",
            (guild_id, word.lower(), severity, added_by)
        )
        self.connection.commit()

    async def get_custom_badwords(self, guild_id: int) -> List[str]:
        """Get all custom badwords for guild."""
        self.cursor.execute(
            "SELECT word FROM custom_badwords WHERE guild_id = ?",
            (guild_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    async def remove_custom_badword(self, guild_id: int, word: str) -> bool:
        """Remove custom badword."""
        self.cursor.execute(
            "DELETE FROM custom_badwords WHERE guild_id = ? AND word = ?",
            (guild_id, word.lower())
        )
        self.connection.commit()
        return self.cursor.rowcount > 0

    # Raid Detection Operations
    async def get_raid_status(self, guild_id: int) -> Dict:
        """Get raid detection status."""
        self.cursor.execute(
            "SELECT * FROM raid_detection WHERE guild_id = ? ORDER BY detection_time DESC LIMIT 1",
            (guild_id,)
        )
        result = self.cursor.fetchone()
        return dict(result) if result else {"join_count": 0, "lockdown_enabled": False}

    async def update_raid_detection(self, guild_id: int, join_count: int, 
                                   suspicious_accounts: int, lockdown_enabled: bool):
        """Update raid detection record."""
        self.cursor.execute(
            """INSERT INTO raid_detection (guild_id, join_count, suspicious_accounts, lockdown_enabled)
               VALUES (?, ?, ?, ?)""",
            (guild_id, join_count, suspicious_accounts, lockdown_enabled)
        )
        self.connection.commit()

    # Backup Operations
    async def record_backup(self, guild_id: int, backup_name: str, backup_type: str, file_path: str):
        """Record backup metadata."""
        self.cursor.execute(
            """INSERT INTO backup_metadata (guild_id, backup_name, backup_type, file_path)
               VALUES (?, ?, ?, ?)""",
            (guild_id, backup_name, backup_type, file_path)
        )
        self.connection.commit()

    async def get_latest_backup(self, guild_id: int, backup_type: str) -> Optional[Dict]:
        """Get latest backup of specific type."""
        self.cursor.execute(
            """SELECT * FROM backup_metadata 
               WHERE guild_id = ? AND backup_type = ?
               ORDER BY created_at DESC LIMIT 1""",
            (guild_id, backup_type)
        )
        result = self.cursor.fetchone()
        return dict(result) if result else None


# Helper to convert database rows to dicts

def dict_factory(cursor, row):
    """Convert database row to dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# Initialize database manager singleton
db_manager: Optional[DatabaseManager] = None


async def init_database(db_type: str = "sqlite", db_path: str = "security_bot.db") -> DatabaseManager:
    """Initialize and return database manager."""
    global db_manager
    db_manager = DatabaseManager(db_type, db_path)
    await db_manager.init_db()
    return db_manager


def get_db() -> DatabaseManager:
    """Get database manager instance."""
    global db_manager
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return db_manager
