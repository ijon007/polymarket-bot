from datetime import datetime, timezone
from loguru import logger
from src.database import log_trade
from src.config import PAPER_MODE


def execute_trade(market, signal):
  """
  Execute trade based on signal.

  Handles special cases:
  - action='bet_both': Execute arbitrage (buy YES and NO)
  - action='bet_yes': Buy YES
  - action='bet_no': Buy NO
  """
  if not PAPER_MODE:
    logger.warning("Real trading not implemented yet")
    return False

  # Handle arbitrage (bet both sides)
  if signal["action"] == "bet_both":
    trade_data = {
      "market_ticker": market.get("slug") or market.get("question") or "unknown",
      "condition_id": market.get("condition_id") or "",
      "question": market.get("question") or "",
      "strategy": signal.get("strategy") or "",
      "action": "ARBITRAGE",
      "side": "ARBITRAGE",
      "price": None,
      "yes_price": signal.get("yes_price"),
      "no_price": signal.get("no_price"),
      "position_size": float(signal.get("size") or 0),
      "size": float(signal.get("size") or 0),
      "expected_profit": float(signal.get("expected_profit") or 0),
      "confidence": float(signal.get("confidence") or 0),
      "reason": signal.get("reason") or "",
      "executed_at": datetime.now(timezone.utc).replace(tzinfo=None),
      "status": "paper",
    }

    logger.info(
      f"PAPER TRADE [ARBITRAGE]: "
      f"Buy YES @ {signal['yes_price']:.4f} + NO @ {signal['no_price']:.4f} | "
      f"Size: ${signal['size']:.2f} | "
      f"Expected: ${signal['expected_profit']:.2f}"
    )

  # Handle directional bets
  else:
    side = "YES" if signal["action"] == "bet_yes" else "NO"

    trade_data = {
      "market_ticker": market.get("slug") or market.get("question") or "unknown",
      "condition_id": market.get("condition_id") or "",
      "question": market.get("question") or "",
      "strategy": signal.get("strategy") or "",
      "action": side,
      "side": side,
      "price": signal.get("price"),
      "yes_price": market.get("yes_price"),
      "no_price": market.get("no_price"),
      "position_size": float(signal.get("size") or 0),
      "size": float(signal.get("size") or 0),
      "expected_profit": float(signal.get("expected_profit") or 0),
      "confidence": float(signal.get("confidence") or 0),
      "reason": signal.get("reason") or "",
      "executed_at": datetime.now(timezone.utc).replace(tzinfo=None),
      "status": "paper",
    }

    logger.info(
      f"PAPER TRADE [{signal['strategy'].upper()}]: "
      f"Buy {side} @ {signal['price']:.4f} | "
      f"Size: ${signal['size']:.2f} | "
      f"Confidence: {signal['confidence']*100:.0f}% | "
      f"Reason: {signal['reason']}"
    )

  saved = log_trade(trade_data)
  if not saved:
    logger.error("Trade was NOT saved to database - check logs above for cause")
  return True
