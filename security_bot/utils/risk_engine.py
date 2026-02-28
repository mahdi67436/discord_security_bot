"""
Intelligent user risk scoring engine.
Analyzes user behavior and assigns risk scores.
"""

import logging
from typing import Dict
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class RiskEngine:
    """Intelligent risk scoring for users."""

    # Risk score thresholds
    LOW_RISK_THRESHOLD = 20.0
    MEDIUM_RISK_THRESHOLD = 50.0
    HIGH_RISK_THRESHOLD = 75.0

    # Risk deltas for different infractions
    RISK_DELTAS = {
        "badword_violation": 5.0,
        "spam_warning": 3.0,
        "invite_posting": 8.0,
        "malicious_link": 15.0,
        "rapid_escalation": 25.0,
        "raid_attempt": 30.0,
        "ban_bypass": 40.0,
    }

    @staticmethod
    def get_risk_level(score: float) -> str:
        """Get risk level string."""
        if score < RiskEngine.LOW_RISK_THRESHOLD:
            return "🟢 Low"
        elif score < RiskEngine.MEDIUM_RISK_THRESHOLD:
            return "🟡 Medium"
        elif score < RiskEngine.HIGH_RISK_THRESHOLD:
            return "🔴 High"
        else:
            return "🔴🔴 Critical"

    @staticmethod
    def calculate_infraction_score(infraction_type: str, severity: str = "normal") -> float:
        """
        Calculate risk score for infraction.
        
        Args:
            infraction_type: Type of infraction
            severity: 'low', 'normal', 'high'
        
        Returns:
            Risk score delta
        """
        base_score = RiskEngine.RISK_DELTAS.get(infraction_type, 5.0)

        multiplier = {
            "low": 0.5,
            "normal": 1.0,
            "high": 1.5,
        }.get(severity, 1.0)

        return base_score * multiplier

    @staticmethod
    def analyze_account_age(join_date: datetime) -> float:
        """
        Analyze account age for suspicious behavior.
        
        Returns:
            Risk delta
        """
        days_old = (datetime.now(timezone.utc) - join_date).days

        if days_old < 1:
            return 20.0  # Brand new account
        elif days_old < 7:
            return 15.0  # Less than a week
        elif days_old < 30:
            return 8.0   # Less than a month
        else:
            return 0.0   # Established account

    @staticmethod
    def analyze_message_velocity(message_count: int, time_window_minutes: int = 60) -> float:
        """
        Analyze rapid message sending.
        
        Returns:
            Risk delta
        """
        messages_per_minute = message_count / max(time_window_minutes, 1)

        if messages_per_minute > 10:
            return 25.0
        elif messages_per_minute > 5:
            return 15.0
        elif messages_per_minute > 2:
            return 8.0
        else:
            return 0.0

    @staticmethod
    def analyze_role_history(role_changes_24h: int) -> float:
        """
        Analyze suspicious role changes.
        
        Returns:
            Risk delta
        """
        if role_changes_24h > 5:
            return 30.0  # Rapid role manipulation
        elif role_changes_24h > 3:
            return 15.0
        elif role_changes_24h > 1:
            return 8.0
        else:
            return 0.0

    @staticmethod
    def analyze_permission_escalation(has_admin: bool, has_mod: bool,
                                     role_change_speed_seconds: int) -> float:
        """
        Analyze permission escalation patterns.
        
        Returns:
            Risk delta
        """
        if has_admin:
            if role_change_speed_seconds < 300:  # 5 minutes
                return 40.0  # Rapid admin gain
            return 25.0  # Has admin

        if has_mod:
            if role_change_speed_seconds < 600:  # 10 minutes
                return 20.0
            return 10.0

        return 0.0

    @staticmethod
    def analyze_activity_patterns(infractions_24h: int, infractions_7d: int) -> Dict:
        """
        Analyze activity patterns for anomalies.
        
        Returns:
            Pattern analysis with risk delta
        """
        pattern = {
            "infractions_24h": infractions_24h,
            "infractions_7d": infractions_7d,
            "frequency": "normal",
            "risk_delta": 0.0,
        }

        if infractions_24h > 5:
            pattern["frequency"] = "spike"
            pattern["risk_delta"] = 30.0
        elif infractions_24h > 2:
            pattern["frequency"] = "elevated"
            pattern["risk_delta"] = 15.0
        elif infractions_7d > 10:
            pattern["frequency"] = "sustained"
            pattern["risk_delta"] = 20.0

        return pattern

    @staticmethod
    def calculate_trust_score(member) -> float:
        """
        Global trust score calculation before any infractions.
        
        Args:
            member: discord.Member object
        
        Returns:
            Initial trust score (inverse of risk)
        """
        score = 0.0

        # Account age analysis
        join_risk = RiskEngine.analyze_account_age(member.joined_at)
        score += join_risk

        # Account creation age
        creation_risk = RiskEngine.analyze_account_age(member.created_at)
        score += creation_risk

        # Roles count (established members less suspicious)
        if len(member.roles) > 5:
            score -= 5.0  # Good sign
        elif len(member.roles) < 2 and member.top_role == member.guild.default_role:
            score += 10.0  # Suspicious

        # No avatar
        if not member.avatar:
            score += 5.0

        # Account flags
        if member.bot:
            score += 2.0

        return min(100.0, max(0.0, score))

    @staticmethod
    def get_recommended_action(risk_score: float) -> str:
        """Get recommended action based on risk score."""
        if risk_score < RiskEngine.LOW_RISK_THRESHOLD:
            return "Monitor"
        elif risk_score < RiskEngine.MEDIUM_RISK_THRESHOLD:
            return "Watch"
        elif risk_score < RiskEngine.HIGH_RISK_THRESHOLD:
            return "Restrict"
        else:
            return "Ban"


class BehaviorAnalyzer:
    """Analyze user behavior patterns."""

    def __init__(self):
        self.user_behavior = {}

    async def track_action(self, user_id: int, action_type: str):
        """Track user action."""
        if user_id not in self.user_behavior:
            self.user_behavior[user_id] = []

        self.user_behavior[user_id].append({
            "type": action_type,
            "timestamp": datetime.now(timezone.utc),
        })

        # Clean old entries (>24h)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self.user_behavior[user_id] = [
            b for b in self.user_behavior[user_id]
            if b["timestamp"] > cutoff
        ]

    async def get_behavior_summary(self, user_id: int) -> Dict:
        """Get user behavior summary."""
        if user_id not in self.user_behavior:
            return {"actions_24h": 0, "action_types": {}}

        actions = self.user_behavior[user_id]
        action_types = {}

        for action in actions:
            action_type = action["type"]
            action_types[action_type] = action_types.get(action_type, 0) + 1

        return {
            "actions_24h": len(actions),
            "action_types": action_types,
        }
