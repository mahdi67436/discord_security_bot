"""
Database models and schema definitions.
Already implemented in db.py but this serves as documentation.
"""

"""
Database Schema Overview:

1. guild_configs
   - guild_id (PRIMARY KEY)
   - antinuke_enabled (BOOLEAN)
   - antiraid_enabled (BOOLEAN)
   - antibot_enabled (BOOLEAN)
   - antibadword_enabled (BOOLEAN)
   - antilink_enabled (BOOLEAN)
   - security_role_id (INTEGER)
   - log_channel_id (INTEGER)
   - lockdown_mode (BOOLEAN)
   - created_at (TIMESTAMP)
   - updated_at (TIMESTAMP)

2. user_warnings
   - warning_id (PRIMARY KEY)
   - guild_id (FK)
   - user_id (INTEGER)
   - reason (TEXT)
   - moderator_id (INTEGER)
   - created_at (TIMESTAMP)

3. user_risk_scores
   - score_id (PRIMARY KEY)
   - guild_id (FK)
   - user_id (INTEGER)
   - risk_score (REAL 0-100)
   - warning_count (INTEGER)
   - last_infraction (TIMESTAMP)
   - flag_reason (TEXT)
   - updated_at (TIMESTAMP)

4. whitelisted_users
   - whitelist_id (PRIMARY KEY)
   - guild_id (FK)
   - user_id (INTEGER)
   - reason (TEXT)
   - added_by (INTEGER)
   - created_at (TIMESTAMP)

5. whitelisted_bots
   - bot_whitelist_id (PRIMARY KEY)
   - guild_id (FK)
   - bot_id (INTEGER)
   - reason (TEXT)
   - added_by (INTEGER)
   - created_at (TIMESTAMP)

6. whitelisted_links
   - link_whitelist_id (PRIMARY KEY)
   - guild_id (FK)
   - domain (TEXT)
   - reason (TEXT)
   - added_by (INTEGER)
   - created_at (TIMESTAMP)

7. custom_badwords
   - badword_id (PRIMARY KEY)
   - guild_id (FK)
   - word (TEXT)
   - severity (TEXT: low/medium/high)
   - added_by (INTEGER)
   - created_at (TIMESTAMP)

8. audit_log_cache
   - cache_id (PRIMARY KEY)
   - guild_id (FK)
   - action_type (TEXT)
   - user_id (INTEGER)
   - target_id (INTEGER)
   - timestamp (TIMESTAMP)

9. raid_detection
   - raid_id (PRIMARY KEY)
   - guild_id (FK)
   - join_count (INTEGER)
   - suspicious_accounts (INTEGER)
   - lockdown_enabled (BOOLEAN)
   - detection_time (TIMESTAMP)

10. backup_metadata
    - backup_id (PRIMARY KEY)
    - guild_id (FK)
    - backup_name (TEXT)
    - backup_type (TEXT: auto/manual)
    - file_path (TEXT)
    - created_at (TIMESTAMP)
"""
