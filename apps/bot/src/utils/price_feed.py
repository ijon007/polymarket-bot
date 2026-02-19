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
    return get_latest_btc_usd()
  except Exception as e:
    logger.debug(f"RTDS unavailable: {e}")
  return None


def _price_at_timestamp(ts: int, asset: str, rtds_fn_name: str) -> Optional[float]:
  """Lookup price at ts via RTDS; None if no data for that asset yet."""
  if ts <= 0:
    return None
  try:
    from src.utils import rtds_client
    rtds_fn = getattr(rtds_client, rtds_fn_name)
    return rtds_fn(ts)
  except Exception as e:
    logger.debug(f"RTDS start price lookup {asset}: {e}")
    return None


def get_btc_price_at_timestamp(ts: int) -> Optional[float]:
  """BTC price at a Unix timestamp (e.g. 15min window start). None if no data yet."""
  return _price_at_timestamp(ts, "btc", "get_btc_at_timestamp")


def get_eth_price_at_timestamp(ts: int) -> Optional[float]:
  """ETH price at a Unix timestamp. None if no data yet."""
  return _price_at_timestamp(ts, "eth", "get_eth_at_timestamp")


def get_sol_price_at_timestamp(ts: int) -> Optional[float]:
  """SOL price at a Unix timestamp. None if no data yet."""
  return _price_at_timestamp(ts, "sol", "get_sol_at_timestamp")


def get_xrp_price_at_timestamp(ts: int) -> Optional[float]:
  """XRP price at a Unix timestamp. None if no data yet."""
  return _price_at_timestamp(ts, "xrp", "get_xrp_at_timestamp")


# --- Asset-agnostic API (5-min multi-asset) ---
def _get_latest_usd(asset: str) -> Optional[float]:
  """Dispatch to rtds_client get_latest_*_usd by asset."""
  try:
    from src.utils import rtds_client
    fn_name = f"get_latest_{asset}_usd"
    fn = getattr(rtds_client, fn_name, None)
    return fn() if callable(fn) else None
  except Exception:
    return None


_GET_PRICE_AT_TS_FNS = {
  "btc": get_btc_price_at_timestamp,
  "eth": get_eth_price_at_timestamp,
  "sol": get_sol_price_at_timestamp,
  "xrp": get_xrp_price_at_timestamp,
}


def get_price(asset: str) -> Optional[float]:
  """Current price for asset (btc/eth/sol/xrp) from RTDS. None if unavailable."""
  a = (asset or "").strip().lower()
  if a not in _GET_PRICE_AT_TS_FNS:
    return None
  return _get_latest_usd(a)


def get_price_at_timestamp(ts: int, asset: str) -> Optional[float]:
  """Price at Unix timestamp for asset (btc/eth/sol/xrp). None if no data yet."""
  a = (asset or "").strip().lower()
  fn = _GET_PRICE_AT_TS_FNS.get(a)
  if not fn:
    return None
  return fn(ts) if ts > 0 else None


def get_price_source(asset: str) -> Optional[str]:
  """Return 'rtds' if current price is available for asset, else None."""
  if get_price(asset) is not None:
    return "rtds"
  return None
