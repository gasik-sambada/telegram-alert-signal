"""Forward trade signals to the bybit-auto-trade service."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import httpx

if TYPE_CHECKING:
    from .config import AutoTradeConfig

logger = logging.getLogger(__name__)

# Default timeout for pushing to the auto-trade service (seconds)
_TIMEOUT = 10.0


def _build_trade_payload(data: dict) -> Optional[dict]:
    """
    Build the JSON payload to send to the bybit-auto-trade /trade endpoint.

    Supported actions from TradingView:
      - open        → open a new position
      - close_all   → close all positions for the symbol
      - update_sl_tp→ update SL/TP on open positions
      - signal      → directional signal only, no order details → skip

    Symbol handling:
      - Exchange prefix is stripped:  "BINANCE:BTCUSDT.P" → "BTCUSDT.P"
      - .P suffix is PRESERVED:       "BTCUSDT.P" stays "BTCUSDT.P"
        (bybit-auto-trade uses .P to identify perpetual futures)

    Returns None if the payload should not be forwarded.
    """
    action = data.get("action", "")
    symbol = data.get("symbol", "")

    if not action or not symbol:
        return None

    # Strip exchange prefix only (e.g. "BINANCE:BTCUSDT.P" → "BTCUSDT.P")
    # Do NOT strip .P — bybit-auto-trade uses it to identify perpetual futures
    if ":" in symbol:
        symbol = symbol.split(":", 1)[1]

    if action == "open":
        payload = {
            "action": "open",
            "symbol": symbol.upper(),
            "side":   data.get("side", ""),       # BUY or SELL
            "price":  str(data.get("price", "")),
            "sl":     str(data.get("sl", "")),
            "tp":     str(data.get("tp", "")),
        }
        # Forward order_type if TradingView sent it; bybit-auto-trade uses it
        # to override per-symbol default (Market vs Limit). If absent, the
        # auto-trade service falls back to its own default (Market).
        order_type = data.get("order_type") or data.get("orderType")
        if order_type:
            payload["order_type"] = str(order_type)

        return payload

    if action == "close_all":
        return {
            "action": "close_all",
            "symbol": symbol.upper(),
        }

    if action == "update_sl_tp":
        payload = {
            "action": "update_sl_tp",
            "symbol": symbol.upper(),
        }
        sl = data.get("sl")
        tp = data.get("tp")
        if sl:
            payload["sl"] = str(sl)
        if tp:
            payload["tp"] = str(tp)
        if not sl and not tp:
            logger.warning(f"[AutoTrade] update_sl_tp for {symbol} has no sl or tp values — skipping")
            return None
        return payload

    # "signal" and other actions carry no order details — nothing to trade
    logger.debug(f"[AutoTrade] Skipping action '{action}' for {symbol}")
    return None


async def push_auto_trade(cfg: "AutoTradeConfig", data: dict) -> bool:
    """
    Asynchronously push a trade payload to the bybit-auto-trade service.

    This is fire-and-forget: failures are logged but never raised so that
    Telegram delivery is never impacted.

    Returns True on success, False on any error.
    """
    payload = _build_trade_payload(data)
    if payload is None:
        return True  # Nothing to push — not an error

    action = payload["action"]
    endpoint = "/trade" if action == "open" else "/close"
    url = cfg.url.rstrip("/") + endpoint

    headers = {"Content-Type": "application/json"}
    if cfg.secret:
        headers["X-Auto-Trade-Secret"] = cfg.secret

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code == 200:
            logger.info(
                f"[AutoTrade] ✅ Pushed {action} for {payload.get('symbol')} → {url}"
            )
            return True
        else:
            logger.error(
                f"[AutoTrade] ❌ HTTP {resp.status_code} from {url}: {resp.text[:300]}"
            )
            return False

    except httpx.TimeoutException:
        logger.error(f"[AutoTrade] ⏱️ Timeout pushing to {url}")
        return False
    except Exception as exc:
        logger.error(f"[AutoTrade] 💥 Error pushing to {url}: {exc}")
        return False
