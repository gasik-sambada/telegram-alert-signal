import json
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status

from .config import Config
from .formatter import format_alert
from .telegram import send_to_targets
from .auto_trade import push_auto_trade

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
    if config.auto_trade.enabled:
        logger.info(f"   Auto-trade URL:     {config.auto_trade.url}")
        logger.info(f"   Auto-trade symbols: {sorted(config.auto_trade.symbols) or ['(all disabled)']}")
        logger.info(f"   Auto-trade secret:  {'✅ set' if config.auto_trade.secret else '⚠️  not set'}")
    else:
        logger.info("   Auto-trade:         ⚠️  disabled (AUTO_TRADE_URL not set)")
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


@app.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return "OK"


@app.post("/webhook")
async def webhook(request: Request):
    """
    Receive TradingView alert webhooks.

    TradingView sends the alert message as the raw POST body.
    The body is the JSON string from our Pine Script alert() calls.
    """
    try:
        # ── Validate webhook secret (if configured) ──────────────────────────
        if config.webhook_secret:
            secret = request.headers.get("X-Webhook-Secret", "")
            if secret != config.webhook_secret:
                logger.warning(f"Invalid webhook secret from {request.client.host}")
                return Response(
                    content="Unauthorized",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

        # ── Parse body ───────────────────────────────────────────────────────
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8").strip()
        logger.info(f"📩 Raw body: {body_str[:500]}")

        try:
            data = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {"status": "error", "error": f"Invalid JSON: {str(e)}"}

        action = data.get("action", "unknown")
        symbol = data.get("symbol", "unknown")
        logger.info(f"📩 Parsed: action={action} symbol={symbol}")

        # ── Get target chats ─────────────────────────────────────────────────
        targets = config.get_targets(symbol)
        if not targets:
            logger.warning(f"No chat targets for symbol '{symbol}', skipping")
            return {"status": "skipped", "reason": "no_chat_targets", "symbol": symbol}

        logger.info(f"📍 Targets: {[repr(t) for t in targets]}")

        # ── Format message ───────────────────────────────────────────────────
        message = format_alert(data)
        logger.info(f"📝 Formatted message ({len(message)} chars)")

        # ── Send to Telegram ─────────────────────────────────────────────────
        if not config.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not set, cannot send")
            return {"status": "error", "error": "Bot token not configured"}

        results = await send_to_targets(config.bot_token, targets, message)

        sent = sum(1 for ok in results.values() if ok)
        failed = sum(1 for ok in results.values() if not ok)

        logger.info(f"✅ Sent to {sent}/{len(targets)} targets (failed: {failed})")

        # ── Auto-trade push (fire-and-forget) ────────────────────────────────
        if config.should_auto_trade(symbol):
            auto_ok = await push_auto_trade(config.auto_trade, data)
            logger.info(f"🤖 Auto-trade push: {'✅ ok' if auto_ok else '❌ failed'}")

        return {
            "status": "ok",
            "action": action,
            "symbol": symbol,
            "sent": sent,
            "failed": failed,
            "results": {k: "ok" if v else "failed" for k, v in results.items()},
        }

    except Exception as e:
        # Catch-all: log the full traceback so we can debug from container logs
        tb = traceback.format_exc()
        logger.error(f"💥 Unhandled exception in /webhook:\n{tb}")
        return {"status": "error", "error": str(e), "traceback": tb}
