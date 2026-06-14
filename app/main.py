import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status

from .config import Config
from .formatter import format_alert
from .telegram import send_to_targets

# ── Load config ──────────────────────────────────────────────────────────────────
config = Config.from_env()

# ── Logging ──────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("alert-signal")


# ── App lifecycle ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 TradingView → Telegram Alert Service started")
    logger.info(f"   Symbols configured: {list(config.symbol_chat_map.keys()) or ['(using defaults)']}")
    logger.info(f"   Default targets:    {config.default_targets or ['(none)']}")
    logger.info(f"   Webhook secret:     {'✅ set' if config.webhook_secret else '⚠️  not set'}")
    yield
    logger.info("👋 Alert service stopped")


# ── FastAPI app ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TradingView Telegram Alert",
    version="1.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint for Coolify / load balancers."""
    return {
        "status": "ok",
        "bot_configured": bool(config.bot_token),
        "symbols": list(config.symbol_chat_map.keys()),
    }


@app.post("/webhook")
async def webhook(request: Request):
    """
    Receive TradingView alert webhooks.

    TradingView sends the alert message as the raw POST body.
    The body is the JSON string from our Pine Script alert() calls.
    """
    # ── Validate webhook secret (if configured) ──────────────────────────────
    if config.webhook_secret:
        secret = request.headers.get("X-Webhook-Secret", "")
        if secret != config.webhook_secret:
            logger.warning(f"Invalid webhook secret from {request.client.host}")
            return Response(
                content="Unauthorized",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

    # ── Parse body ───────────────────────────────────────────────────────────
    try:
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8").strip()
        data = json.loads(body_str)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse request body: {e}")
        logger.debug(f"Raw body: {raw_body[:500]}")
        return Response(
            content="Invalid JSON",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    action = data.get("action", "unknown")
    symbol = data.get("symbol", "unknown")
    logger.info(f"📩 Received: action={action} symbol={symbol}")

    # ── Get target chats ─────────────────────────────────────────────────────
    targets = config.get_targets(symbol)
    if not targets:
        logger.warning(f"No chat targets for symbol '{symbol}', skipping")
        return {"status": "skipped", "reason": "no_chat_targets"}

    # ── Format message ───────────────────────────────────────────────────────
    message = format_alert(data)

    # ── Send to Telegram ─────────────────────────────────────────────────────
    if not config.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set, cannot send")
        return Response(
            content="Bot token not configured",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    results = await send_to_targets(config.bot_token, targets, message)

    sent = sum(1 for ok in results.values() if ok)
    failed = sum(1 for ok in results.values() if not ok)

    logger.info(f"✅ Sent to {sent}/{len(targets)} targets (failed: {failed})")

    return {
        "status": "ok",
        "action": action,
        "symbol": symbol,
        "sent": sent,
        "failed": failed,
    }
