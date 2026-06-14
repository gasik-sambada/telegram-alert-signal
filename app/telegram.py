from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import httpx

if TYPE_CHECKING:
    from .config import ChatTarget

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


async def send_message(
    bot_token: str,
    chat_id: str,
    text: str,
    topic_id: Optional[int] = None,
) -> bool:
    """Send a message to a Telegram chat (optionally to a specific topic/thread).
    Returns True on success.
    """
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    # Add topic (forum thread) if specified
    if topic_id is not None:
        payload["message_thread_id"] = topic_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code == 200:
            dest = f"{chat_id}#{topic_id}" if topic_id else chat_id
            logger.info(f"Message sent to {dest}")
            return True
        else:
            logger.error(
                f"Telegram API error for chat {chat_id}: "
                f"{resp.status_code} — {resp.text}"
            )
            return False

    except httpx.TimeoutException:
        logger.error(f"Timeout sending message to chat {chat_id}")
        return False
    except Exception as e:
        logger.error(f"Error sending message to chat {chat_id}: {e}")
        return False


async def send_to_targets(
    bot_token: str,
    targets: list["ChatTarget"],
    text: str,
) -> dict[str, bool]:
    """Send a message to multiple ChatTargets. Returns results per target."""
    results = {}
    for target in targets:
        key = repr(target)
        ok = await send_message(bot_token, target.chat_id, text, target.topic_id)
        results[key] = ok
    return results
