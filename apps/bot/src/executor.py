from datetime import datetime, timezone
from loguru import logger
from src.database import log_trade
from src.config import PAPER_MODE


def execute_trade(market, signal):
  """
  Execute trade based on signal. action='bet_yes' or 'bet_no' only.
  """
  if not PAPER_MODE:
    return _execute_real_trade(market, signal)

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
  for k in ("signal_type", "confidence_layers", "market_end_time"):
    if signal.get(k) is not None:
      trade_data[k] = signal[k]

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


def _execute_real_trade(market, signal):
  """Real trade via CLOB market order. bet_yes / bet_no only."""
  tokens = market.get("tokens") or {}
  side = "YES" if signal["action"] == "bet_yes" else "NO"
  token_id = tokens.get("yes") if side == "YES" else tokens.get("no")
  if not token_id:
    logger.error(f"Missing token_id for {side} - market has no clobTokenIds")
    return False

  position_size = float(signal.get("size") or 0)
  if position_size <= 0:
    logger.error("Position size must be > 0")
    return False

  from src.clob_client import place_market_order, get_balance_allowance

  bal = get_balance_allowance(asset_type="COLLATERAL")
  if bal:
    try:
      balance = float(bal.get("balance") or 0)
      if balance < position_size:
        logger.error(f"Insufficient balance: ${balance:.2f} < ${position_size:.2f}")
        return False
    except (TypeError, ValueError):
      pass

  resp = place_market_order(token_id=token_id, amount_dollars=position_size, side="BUY")
  if not resp.get("success"):
    logger.error(f"CLOB order failed: {resp.get('errorMsg', 'unknown')}")
    return False

  order_id = resp.get("orderID", "")
  tx_hashes = resp.get("transactionsHashes") or []
  if isinstance(tx_hashes, str):
    tx_hashes = [tx_hashes] if tx_hashes else []

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
    "position_size": position_size,
    "size": position_size,
    "expected_profit": float(signal.get("expected_profit") or 0),
    "confidence": float(signal.get("confidence") or 0),
    "reason": signal.get("reason") or "",
    "executed_at": datetime.now(timezone.utc).replace(tzinfo=None),
    "status": "paper",
    "polymarket_order_id": order_id,
    "transaction_hashes": tx_hashes,
  }

  logger.info(
    f"REAL TRADE [{signal['strategy'].upper()}]: "
    f"Buy {side} | Size: ${position_size:.2f} | OrderID: {order_id}"
  )

  saved = log_trade(trade_data)
  if not saved:
    logger.error("Trade was NOT saved to database - check logs above for cause")
  return saved
