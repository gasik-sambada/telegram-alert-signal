import logging
import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


async def send_message(bot_token: str, chat_id: str, text: str) -> bool:
    """Send a message to a Telegram chat. Returns True on success."""
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code == 200:
            logger.info(f"Message sent to chat {chat_id}")
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


async def send_to_chats(bot_token: str, chat_ids: list[str], text: str) -> dict:
    """Send a message to multiple chats. Returns results per chat_id."""
    results = {}
    for chat_id in chat_ids:
        ok = await send_message(bot_token, chat_id, text)
        results[chat_id] = ok
    return results
