import os
import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    bot_token: str = ""
    # JSON map: {"BTCUSDT": ["-100123", "-100456"], "ETHUSDT": ["-100789"]}
    symbol_chat_map: dict[str, list[str]] = field(default_factory=dict)
    # Fallback chat IDs for symbols not in the map
    default_chat_ids: list[str] = field(default_factory=list)
    # Optional webhook secret for request validation
    webhook_secret: str = ""
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN is not set!")

        # Parse symbol → chat ID mapping
        symbol_chat_raw = os.getenv("SYMBOL_CHAT_MAP", "{}")
        try:
            symbol_chat_map = json.loads(symbol_chat_raw)
        except json.JSONDecodeError:
            logger.error("Invalid SYMBOL_CHAT_MAP JSON, using empty map")
            symbol_chat_map = {}

        # Parse default chat IDs (comma-separated)
        default_raw = os.getenv("DEFAULT_CHAT_IDS", "")
        default_chat_ids = [cid.strip() for cid in default_raw.split(",") if cid.strip()]

        webhook_secret = os.getenv("WEBHOOK_SECRET", "")
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        log_level = os.getenv("LOG_LEVEL", "INFO")

        return cls(
            bot_token=bot_token,
            symbol_chat_map=symbol_chat_map,
            default_chat_ids=default_chat_ids,
            webhook_secret=webhook_secret,
            host=host,
            port=port,
            log_level=log_level,
        )

    def get_chat_ids(self, symbol: str) -> list[str]:
        """Get chat IDs for a given symbol. Falls back to default if not mapped."""
        # Try exact match first
        if symbol in self.symbol_chat_map:
            return self.symbol_chat_map[symbol]

        # Try case-insensitive match
        for key, ids in self.symbol_chat_map.items():
            if key.upper() == symbol.upper():
                return ids

        # Fallback to default
        if self.default_chat_ids:
            return self.default_chat_ids

        logger.warning(f"No chat IDs configured for symbol '{symbol}' and no defaults set")
        return []
