"""Format TradingView alert JSON into rich Telegram messages."""


def format_open_order(data: dict) -> str:
    """Format an 'open' action alert into a Telegram message."""
    side = data.get("side", "unknown").upper()
    symbol = data.get("symbol", "???")
    signal_id = data.get("id", "???")
    price = data.get("price", 0)
    qty = data.get("qty", 0)
    sl = data.get("sl", 0)
    tp = data.get("tp", 0)

    is_buy = side == "BUY"
    emoji = "🟢" if is_buy else "🔴"
    direction = "LONG" if is_buy else "SHORT"

    # Detect if this is an add-on order (id ends with _1, _2, etc.)
    is_addon = not signal_id.endswith("_0")
    header = f"📈 ADD {direction}" if is_addon else f"{emoji} OPEN {direction}"

    return (
        f"{header} — <b>{symbol}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Signal ID: <code>{signal_id}</code>\n"
        f"{'🟢' if is_buy else '🔴'} Side: <b>{side}</b>\n"
        f"💰 Price: <b>{_fmt_price(price)}</b>\n"
        f"📊 Qty: <b>{_fmt_qty(qty)}</b>\n"
        f"🛑 SL: <b>{_fmt_price(sl)}</b>\n"
        f"🎯 TP: <b>{_fmt_price(tp)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )


def format_close_all(data: dict) -> str:
    """Format a 'close_all' action alert into a Telegram message."""
    symbol = data.get("symbol", "???")
    ids = data.get("ids", [])
    reason = data.get("reason", "unknown")

    reason_text = {
        "supertrend_reversal": "⚡ SuperTrend Reversal",
        "smc_opposite": "📊 SMC Opposite Break",
    }.get(reason, reason)

    ids_str = ", ".join(f"<code>{i}</code>" for i in ids)

    return (
        f"⚠️ CLOSE ALL — <b>{symbol}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Signals: {ids_str}\n"
        f"📝 Reason: {reason_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )


def format_update_sl_tp(data: dict) -> str:
    """Format an 'update_sl_tp' action alert into a Telegram message."""
    symbol = data.get("symbol", "???")
    ids = data.get("ids", [])
    sl = data.get("sl", 0)
    tp = data.get("tp", 0)

    ids_str = ", ".join(f"<code>{i}</code>" for i in ids)

    return (
        f"🔄 UPDATE SL/TP — <b>{symbol}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Signals: {ids_str}\n"
        f"🛑 SL: <b>{_fmt_price(sl)}</b>\n"
        f"🎯 TP: <b>{_fmt_price(tp)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )


def format_alert(data: dict) -> str:
    """Route to the correct formatter based on the action field."""
    action = data.get("action", "")

    formatters = {
        "open": format_open_order,
        "close_all": format_close_all,
        "update_sl_tp": format_update_sl_tp,
    }

    formatter = formatters.get(action)
    if formatter:
        return formatter(data)

    # Unknown action — dump raw JSON
    return f"❓ Unknown alert:\n<pre>{_safe_json(data)}</pre>"


def _fmt_price(value) -> str:
    """Format a price value."""
    try:
        v = float(value)
        # Use appropriate decimal places based on magnitude
        if v >= 1000:
            return f"{v:,.2f}"
        elif v >= 1:
            return f"{v:,.4f}"
        else:
            return f"{v:.8f}"
    except (ValueError, TypeError):
        return str(value)


def _fmt_qty(value) -> str:
    """Format a quantity value."""
    try:
        v = float(value)
        if v >= 1:
            return f"{v:,.4f}"
        else:
            return f"{v:.8f}"
    except (ValueError, TypeError):
        return str(value)


def _safe_json(data: dict) -> str:
    """Safely serialize dict to JSON string for display."""
    import json

    try:
        return json.dumps(data, indent=2)
    except Exception:
        return str(data)
