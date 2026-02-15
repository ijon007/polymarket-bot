from loguru import logger
from typing import Optional


def get_btc_price_source() -> Optional[str]:
  """Return 'rtds' if current price is available from RTDS, else None."""
  try:
    from src.utils.rtds_client import get_latest_btc_usd
    if get_latest_btc_usd() is not None:
      return "rtds"
  except Exception:
    pass
  return None


def get_btc_price() -> Optional[float]:
  """Fetch current BTC price from RTDS (Chainlink)."""
  try:
    from src.utils.rtds_client import get_latest_btc_usd
    price = get_latest_btc_usd()
    if price is not None:
      logger.debug(f"BTC price (RTDS): ${price:,.2f}")
      return price
  except Exception as e:
    logger.debug(f"RTDS unavailable: {e}")
  return None


def get_btc_price_at_timestamp(ts: int) -> Optional[float]:
  """
  BTC price at a Unix timestamp (e.g. 5min window start).
  Uses RTDS buffer (Chainlink). If we joined mid-window, buffer has no start → None → skip this window, trade next.
  """
  if ts <= 0:
    return None
  try:
    from src.utils.rtds_client import get_btc_at_timestamp as rtds_at_ts
    price = rtds_at_ts(ts)
    if price is not None:
      logger.debug(f"Start price (RTDS) at {ts}: ${price:,.2f}")
      return price
    logger.debug(f"No RTDS start price at {ts} (joined mid-window? skipping this window)")
    return None
  except Exception as e:
    logger.debug(f"RTDS start price lookup: {e}")
    return None
