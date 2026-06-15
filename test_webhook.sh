#!/bin/bash
# =============================================================================
# Test curls for TradingView → Telegram Alert webhook
# =============================================================================
# Usage:
#   chmod +x test_webhook.sh
#   ./test_webhook.sh                     # uses localhost:8000
#   ./test_webhook.sh https://your.domain # uses your deployed URL
# =============================================================================

BASE_URL="${1:-http://localhost:8000}"

echo "🔗 Target: $BASE_URL"
echo ""

# ─── 1. Health Check ────────────────────────────────────────────────────────────
echo "━━━ 1. Health Check ━━━"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

# ─── 2. Open Long Order ─────────────────────────────────────────────────────────
echo "━━━ 2. Open Long Order ━━━"
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "open",
    "symbol": "BTCUSDT.P",
    "id": "Long_0",
    "side": "buy",
    "price": 104325.50,
    "qty": 0.00479,
    "sl": 103850.00,
    "tp": 112038.75
  }' | python3 -m json.tool
echo ""

# ─── 3. Open Short Order ────────────────────────────────────────────────────────
echo "━━━ 3. Open Short Order ━━━"
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "open",
    "symbol": "BTCUSDT.P",
    "id": "Short_0",
    "side": "sell",
    "price": 104325.50,
    "qty": 0.00512,
    "sl": 104890.00,
    "tp": 96213.50
  }' | python3 -m json.tool
echo ""

# ─── 4. SMC Add-on Order ────────────────────────────────────────────────────────
echo "━━━ 4. SMC Add-on Long ━━━"
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "open",
    "symbol": "BTCUSDT.P",
    "id": "Long_1",
    "side": "buy",
    "price": 105100.00,
    "qty": 0.00465,
    "sl": 104200.00,
    "tp": 112308.00
  }' | python3 -m json.tool
echo ""

# ─── 5. Update SL/TP ────────────────────────────────────────────────────────────
echo "━━━ 5. Update SL/TP ━━━"
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update_sl_tp",
    "symbol": "BTCUSDT.P",
    "ids": ["Long_0", "Long_1"],
    "sl": 104500.00,
    "tp": 112600.00
  }' | python3 -m json.tool
echo ""

# ─── 6. Close All (SuperTrend Reversal) ─────────────────────────────────────────
echo "━━━ 6. Close All (reversal) ━━━"
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "close_all",
    "symbol": "BTCUSDT.P",
    "ids": ["Long_0", "Long_1"],
    "reason": "supertrend_reversal"
  }' | python3 -m json.tool
echo ""

# ─── 7. Close All (SMC Opposite) ────────────────────────────────────────────────
echo "━━━ 7. Close All (SMC opposite) ━━━"
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "close_all",
    "symbol": "ETHUSDT.P",
    "ids": ["Short_0", "Short_1", "Short_2"],
    "reason": "smc_opposite"
  }' | python3 -m json.tool
echo ""

echo "✅ All tests done!"

# ─── 8. SuperTrend MTF — Current TF Buy Signal ──────────────────────────────────
echo "━━━ 8. SuperTrend MTF — Current TF Buy ━━━"
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "signal",
    "symbol": "BTCUSDT.P",
    "side": "buy",
    "price": 104325.50,
    "timeframe": "1H",
    "htf": "",
    "indicator": "SuperTrend MTF"
  }' | python3 -m json.tool
echo ""

# ─── 9. SuperTrend MTF — HTF Sell Signal ────────────────────────────────────────
echo "━━━ 9. SuperTrend MTF — HTF Sell ━━━"
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "signal",
    "symbol": "BTCUSDT.P",
    "side": "sell",
    "price": 104100.00,
    "timeframe": "1H",
    "htf": "1D",
    "indicator": "SuperTrend MTF"
  }' | python3 -m json.tool
echo ""

echo "✅ All SuperTrend MTF tests done!"
