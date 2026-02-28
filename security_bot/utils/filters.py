"""
Advanced filtering system for detecting abuse, phishing, and malicious content.
Supports multiple languages, unicode normalization, and leetspeak bypass.
"""

import re
import unicodedata
from typing import List, Tuple, Set
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class TextFilter:
    """Advanced text filtering with multi-language support."""

    # Multi-language badword database (core patterns)
    BADWORD_DATABASE = {
        "english": [
            # Profanity
            r"f[u\*@]ck", r"sh[i\*@]t", r"b[i\*@]tch", r"@ss", r"d@mn",
            r"h[e3][l1]l[o0]", r"[ck]unt", r"n[i1]gg", r"w[h4]0r3?",
            r"sl[u\*@]t", r"d[i\*@]ck", r"c0ck", r"p[u\*@]ssy",
        ],
        "bangla": [
            r"ম[া়়া]দার", r"চোদ", r"গেন্ডু", r"বেটাল", r"মাইর", r"কাহিল",
            r"কামার", r"হারাম", r"জাহান্নাম", r"শয়তান",
        ],
        "hindi": [
            r"माद[ेैा]", r"बस्त", r"चूत", r"हरामी", r"लोड़", r"साल",
            r"भेंचो?द", r"गांड", r"घ्रा", r"पागल",
        ],
        "arabic": [
            r"زنا", r"لعن", r"قذر", r"حمار", r"منيوك", r"وسخ",
            r"خنزير", r"شنيع", r"فاحشة", r"هابط",
        ],
    }


    # Phishing and malicious domains
    MALICIOUS_DOMAINS = {
        "nitro-gen": "Fake Discord Nitro",
        "discord-token": "Token stealer",
        "ip-logger": "IP grabber",
        "grabify": "IP grabber",
        "discord-free": "Phishing",
        "free-nitro": "Phishing",
        "discord-gen": "Token generator",
    }

    # Suspicious TLDs
    SUSPICIOUS_TLDS = [".tk", ".ml", ".ga", ".cf", ".top", ".download", ".accountant"]

    # URL shorteners
    URL_SHORTENERS = ["bit.ly", "tinyurl", "short.link", "goo.gl", "ow.ly"]

    # Common phishing and ip-logger domains
    PHISHING_DOMAINS = [
        "discordapp.link", "discord.gift", "discord.store",  # Not real Discord domains
        "grabify.link", "iplogger.com", "discord-token.com",
    ]

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize Unicode text to catch variations."""
        # NFD normalization
        text = unicodedata.normalize('NFD', text)
        # Remove accents
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.lower()

    @staticmethod
    def leetspeak_normalize(text: str) -> str:
        """Convert common leetspeak patterns."""
        replacements = {
            '@': 'a', '4': 'a', '1': 'i', '3': 'e', '0': 'o',
            '5': 's', '7': 't', '8': 'b', '6': 'g', '!': 'i',
            '$': 's', '2': 'z', '9': 'g', '|': 'i',
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text.lower()

    @staticmethod
    def contains_badword(text: str) -> Tuple[bool, str, str]:
        """
        Check if text contains badwords with multi-language support.
        
        Returns:
            (is_bad, word_found, language)
        """
        text_normalized = TextFilter.normalize_text(text)
        text_leetspeak = TextFilter.leetspeak_normalize(text)

        # Check each language database
        for lang, patterns in TextFilter.BADWORD_DATABASE.items():
            for pattern in patterns:
                # Test against normalized text
                if re.search(pattern, text_normalized, re.IGNORECASE):
                    return True, pattern, lang
                # Test against leetspeak conversion
                if re.search(pattern, text_leetspeak, re.IGNORECASE):
                    return True, pattern, lang

        return False, "", ""

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract all URLs from text."""
        url_pattern = r'https?://[^\s]+'
        return re.findall(url_pattern, text, re.IGNORECASE)

    @staticmethod
    def check_url_safety(url: str) -> Tuple[bool, str]:
        """
        Check if URL is potentially malicious.
        
        Returns:
            (is_safe, reason)
        """
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '')

            # Check against known malicious domains
            for malicious, reason in TextFilter.MALICIOUS_DOMAINS.items():
                if malicious in domain:
                    return False, f"Known malicious: {reason}"

            # Check known phishing domains
            if any(phishing in domain for phishing in TextFilter.PHISHING_DOMAINS):
                return False, "Known phishing domain"

            # Check URL shorteners
            if any(shortener in domain for shortener in TextFilter.URL_SHORTENERS):
                return False, "URL shortener (potential phishing)"

            # Check suspicious TLDs
            if any(domain.endswith(tld) for tld in TextFilter.SUSPICIOUS_TLDS):
                return False, "Suspicious TLD"

            # Discord invite check
            if "discord" not in domain and ("invite" in url or "discord.gg" in url):
                if "discord.gg" not in domain:
                    return False, "Suspicious Discord invite"

            return True, "Safe"

        except Exception as e:
            logger.warning(f"URL parsing error: {e}")
            return False, "Parsing error"

    @staticmethod
    def check_discord_invite(text: str) -> Tuple[bool, List[str]]:
        """
        Check if text contains Discord invite links.
        
        Returns:
            (contains_invite, invite_codes)
        """
        # Discord invite patterns
        patterns = [
            r'(?:https?://)?(?:www\.)?discord(?:\.gg|app\.com/invite)/([a-zA-Z0-9\-_]+)',
            r'(?:discord\.gg/)?([a-zA-Z0-9]{6,})',
        ]

        invites = []
        for pattern in patterns:
            invites.extend(re.findall(pattern, text, re.IGNORECASE))

        return len(invites) > 0, invites


class MessageFilter:
    """Message filtering engine."""

    @staticmethod
    async def check_message(content: str, guild_id: int, custom_badwords: List[str] = None) -> Tuple[bool, str]:
        """
        Comprehensive message check.
        
        Returns:
            (should_delete, reason)
        """
        if not content or len(content) < 2:
            return False, ""

        # Check badwords
        is_bad, word, lang = TextFilter.contains_badword(content)
        if is_bad:
            return True, f"Profanity detected ({lang})"

        # Check custom badwords
        if custom_badwords:
            text_normalized = TextFilter.normalize_text(content)
            for custom_word in custom_badwords:
                if custom_word.lower() in text_normalized:
                    return True, "Custom word violation"

        # Check URLs
        urls = TextFilter.extract_urls(content)
        for url in urls:
            is_safe, reason = TextFilter.check_url_safety(url)
            if not is_safe:
                return True, f"Malicious link: {reason}"

        # Check Discord invites
        has_invite, invites = TextFilter.check_discord_invite(content)
        if has_invite:
            return True, f"Unauthorized invite link"

        return False, ""

class SpamFilter:
    """Spam detection."""

    def __init__(self, max_messages: int = 5, time_window: int = 5):
        """
        Initialize spam filter.
        
        Args:
            max_messages: Max messages before flagged as spam
            time_window: Time window in seconds
        """
        self.max_messages = max_messages
        self.time_window = time_window
        self.message_history = {}

    async def check_spam(self, user_id: int, timestamp: float) -> bool:
        """Check if user is spamming."""
        if user_id not in self.message_history:
            self.message_history[user_id] = []

        current_messages = [
            ts for ts in self.message_history[user_id]
            if timestamp - ts < self.time_window
        ]

        self.message_history[user_id] = current_messages + [timestamp]

        if len(self.message_history[user_id]) > self.max_messages:
            return True

        return False
