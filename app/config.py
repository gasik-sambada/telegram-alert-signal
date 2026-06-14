from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ChatTarget:
    """A single Telegram destination: chat + optional topic (forum thread)."""

    chat_id: str
    topic_id: Optional[int] = None   # message_thread_id for forum topics

    def __repr__(self) -> str:
        if self.topic_id:
            return f"{self.chat_id}#{self.topic_id}"
        return self.chat_id


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    bot_token: str = ""
    # Mapping: symbol → list of ChatTarget
    symbol_chat_map: dict[str, list[ChatTarget]] = field(default_factory=dict)
    # Fallback targets for symbols not in the map
    default_targets: list[ChatTarget] = field(default_factory=list)
    # Optional webhook secret for request validation
    webhook_secret: str = ""
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    @staticmethod
    def _parse_target(entry) -> ChatTarget:
        """
        Parse a single chat target entry. Supports multiple formats:

        String (no topic):       "-100123456789"
        String with topic:       "-100123456789:42"
        Object (full):           {"chat_id": "-100123456789", "topic_id": 42}
        Object (no topic):       {"chat_id": "-100123456789"}
        """
        if isinstance(entry, dict):
            chat_id = str(entry.get("chat_id", ""))
            topic_id = entry.get("topic_id")
            return ChatTarget(
                chat_id=chat_id,
                topic_id=int(topic_id) if topic_id is not None else None,
            )
        elif isinstance(entry, str):
            if ":" in entry:
                parts = entry.rsplit(":", 1)
                try:
                    return ChatTarget(chat_id=parts[0], topic_id=int(parts[1]))
                except ValueError:
                    return ChatTarget(chat_id=entry)
            return ChatTarget(chat_id=entry)
        else:
            return ChatTarget(chat_id=str(entry))

    @classmethod
    def from_env(cls) -> "Config":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN is not set!")

        # Parse symbol → chat target mapping
        symbol_chat_raw = os.getenv("SYMBOL_CHAT_MAP", "{}")
        symbol_chat_map: dict[str, list[ChatTarget]] = {}
        try:
            raw_map = json.loads(symbol_chat_raw)
            for symbol, entries in raw_map.items():
                if isinstance(entries, list):
                    symbol_chat_map[symbol] = [cls._parse_target(e) for e in entries]
                else:
                    # Single entry, not wrapped in a list
                    symbol_chat_map[symbol] = [cls._parse_target(entries)]
        except json.JSONDecodeError:
            logger.error("Invalid SYMBOL_CHAT_MAP JSON, using empty map")

        # Parse default targets (comma-separated "chat_id" or "chat_id:topic_id")
        default_raw = os.getenv("DEFAULT_CHAT_IDS", "")
        default_targets = []
        for entry in default_raw.split(","):
            entry = entry.strip()
            if entry:
                default_targets.append(cls._parse_target(entry))

        webhook_secret = os.getenv("WEBHOOK_SECRET", "")
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        log_level = os.getenv("LOG_LEVEL", "INFO")

        return cls(
            bot_token=bot_token,
            symbol_chat_map=symbol_chat_map,
            default_targets=default_targets,
            webhook_secret=webhook_secret,
            host=host,
            port=port,
            log_level=log_level,
        )

    def get_targets(self, symbol: str) -> list[ChatTarget]:
        """Get chat targets for a given symbol. Falls back to defaults if not mapped."""
        # Try exact match first
        if symbol in self.symbol_chat_map:
            return self.symbol_chat_map[symbol]

        # Try case-insensitive match
        for key, targets in self.symbol_chat_map.items():
            if key.upper() == symbol.upper():
                return targets

        # Fallback to defaults
        if self.default_targets:
            return self.default_targets

        logger.warning(f"No chat targets configured for symbol '{symbol}' and no defaults set")
        return []
