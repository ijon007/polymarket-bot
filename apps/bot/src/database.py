"""Database facade: Convex (when CONVEX_URL set) or no-op."""
import sys
from datetime import datetime, timezone
from loguru import logger

from src.config import CONVEX_URL

# Convex client (lazy init)
_convex_client = None


def _get_client():
  global _convex_client
  if not CONVEX_URL:
    return None
  if _convex_client is None:
    try:
      from convex import ConvexClient
      _convex_client = ConvexClient(CONVEX_URL)
    except Exception as e:
      logger.error(f"Convex client init failed: {e}")
      return None
  return _convex_client


# Columns that must not be None for INSERT
_REQUIRED_KEYS = (
  "market_ticker", "condition_id", "question", "strategy", "action", "side",
  "position_size", "size", "expected_profit", "confidence", "reason", "executed_at", "status"
)


def _sanitize_trade_data(data):
  """Ensure all required fields have non-null values."""
  out = dict(data)
  if not (out.get("market_ticker") or "").strip():
    out["market_ticker"] = out.get("question") or out.get("condition_id") or "unknown"
  for key in _REQUIRED_KEYS:
    if key in out and out[key] is None:
      if key in ("condition_id", "question", "strategy", "action", "side", "reason", "status"):
        out[key] = ""
      elif key in ("position_size", "size", "expected_profit", "confidence"):
        out[key] = 0.0
      elif key == "executed_at":
        out[key] = datetime.now(timezone.utc).replace(tzinfo=None)
  return out


def _to_ms(dt):
  """Convert datetime to Unix milliseconds. Accepts datetime or number. Naive datetimes treated as UTC."""
  if dt is None:
    return None
  if isinstance(dt, (int, float)):
    return int(dt) if dt >= 1e12 else int(dt * 1000)
  if hasattr(dt, "tzinfo") and dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
  return int(dt.timestamp() * 1000)


def _trade_to_convex_payload(data):
  """Convert trade_data to Convex mutation args (executed_at as ms)."""
  safe = _sanitize_trade_data(data)
  executed_at = safe.get("executed_at")
  return {
    "market_ticker": safe.get("market_ticker") or "unknown",
    "condition_id": safe.get("condition_id") or "",
    "question": safe.get("question") or "",
    "strategy": safe.get("strategy") or "",
    "action": safe.get("action") or "",
    "side": safe.get("side") or "",
    "price": safe.get("price"),
    "yes_price": safe.get("yes_price"),
    "no_price": safe.get("no_price"),
    "position_size": float(safe.get("position_size") or 0),
    "size": float(safe.get("size") or 0),
    "expected_profit": float(safe.get("expected_profit") or 0),
    "confidence": float(safe.get("confidence") or 0),
    "reason": safe.get("reason") or "",
    "executed_at": _to_ms(executed_at) or int(datetime.now(timezone.utc).timestamp() * 1000),
    "status": safe.get("status") or "paper",
  }


# Legacy exports for settlement/balance - no-op when using Convex (they use helpers below)
Session = None
Trade = None
MarketOutcome = None


def is_db_configured() -> bool:
  """True when Convex (or legacy DB) is configured."""
  return bool(CONVEX_URL)


def init_db():
  """No-op for Convex (schema is deployed via npx convex dev)."""
  if not CONVEX_URL:
    logger.warning("CONVEX_URL not set - skipping database init")
    return
  logger.info("Database (Convex) ready")


def validate_db_schema():
  """Verify Convex trades table accepts inserts (dry-run)."""
  client = _get_client()
  if not client:
    return
  try:
    payload = _trade_to_convex_payload({
      "market_ticker": "test-dry-run",
      "condition_id": "0x00",
      "question": "test",
      "strategy": "test",
      "action": "YES",
      "side": "YES",
      "price": 0.5,
      "yes_price": 0.5,
      "no_price": 0.5,
      "position_size": 0.0,
      "size": 0.0,
      "expected_profit": 0.0,
      "confidence": 0.0,
      "reason": "DB schema check",
      "executed_at": datetime.now(timezone.utc).replace(tzinfo=None),
      "status": "paper",
    })
    client.mutation("trades:schemaCheck", payload)
    logger.info("DB schema check passed: trades table is compatible")
  except Exception as e:
    raise RuntimeError(
      f"Database schema check FAILED. Fix before trading.\n"
      f"Error: {e}\n"
      f"Run: python scripts/check_db.py"
    ) from e


def has_open_trade_for_market(slug: str) -> bool:
  """True if we already have an unsettled (paper) trade on this market."""
  if not slug:
    return False
  client = _get_client()
  if not client:
    return False
  try:
    return client.query("trades:hasOpenForMarket", {"slug": slug})
  except Exception:
    return False


def log_trade(trade_data):
  """Save trade to database. Never raises. Returns True if saved, False otherwise."""
  client = _get_client()
  if not client:
    logger.warning("Database not configured - trade not logged (set CONVEX_URL in .env.local)")
    return False
  try:
    payload = _trade_to_convex_payload(trade_data)
    trade_id = client.mutation("trades:insert", payload)
    logger.info(f"Trade saved to DB: id={trade_id} market={payload['market_ticker']}")
    return True
  except Exception as e:
    logger.exception(f"Error logging trade to database: {e}")
    return False


# --- Helpers for settlement and balance ---

def list_unsettled_trades():
  """Return list of unsettled (paper) trades from Convex."""
  client = _get_client()
  if not client:
    return []
  try:
    return client.query("trades:listUnsettled", {})
  except Exception:
    return []


def get_market_outcome_by_slug(slug: str):
  """Return market_outcome doc or None."""
  client = _get_client()
  if not client:
    return None
  try:
    return client.query("marketOutcomes:getBySlug", {"slug": slug})
  except Exception:
    return None


def insert_market_outcome(slug: str, condition_id: str, outcome: str, resolved_at_ms: int):
  """Insert a market outcome record."""
  client = _get_client()
  if not client:
    return
  try:
    client.mutation("marketOutcomes:insert", {
      "slug": slug,
      "condition_id": condition_id,
      "outcome": outcome,
      "resolved_at": resolved_at_ms,
    })
  except Exception as e:
    logger.error(f"Error inserting market outcome: {e}")


def update_trade_settlement(trade_id, market_outcome: str, actual_profit: float, status: str, settled_at_ms: int):
  """Update a trade with settlement data."""
  client = _get_client()
  if not client:
    return
  try:
    client.mutation("trades:updateSettlement", {
      "tradeId": trade_id,
      "market_outcome": market_outcome,
      "actual_profit": actual_profit,
      "status": status,
      "settled_at": settled_at_ms,
    })
  except Exception as e:
    logger.error(f"Error updating trade settlement: {e}")


def get_settled_pnl_sum() -> float:
  """Return sum of actual_profit for all settled (won/lost) trades."""
  client = _get_client()
  if not client:
    return 0.0
  try:
    return float(client.query("trades:settledPnLSum", {}) or 0)
  except Exception:
    return 0.0


def list_settled_trades():
  """Return list of settled trades for pnl_summary."""
  client = _get_client()
  if not client:
    return []
  try:
    return client.query("trades:listSettled", {})
  except Exception:
    return []


def init_db_at_url(database_url: str):
  """No-op for Convex. Kept for script compatibility."""
  if database_url and "convex" in database_url.lower():
    logger.info("Convex schema is deployed via npx convex dev")
    return
  raise ValueError("Convex migration: init_db_at_url is not used. Run npx convex dev to deploy schema.")
