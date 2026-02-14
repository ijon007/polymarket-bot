import time
import requests
from loguru import logger
from typing import Optional, Tuple

# Cache to avoid CoinGecko rate limit (429)
_CACHE_SECONDS = 15
_price_cache: Optional[Tuple[float, float]] = None  # (price, timestamp)
_MAX_RETRIES = 3
_RETRY_DELAY = 2


def get_btc_price() -> Optional[float]:
  """Fetch current BTC price from CoinGecko (cached 15s to avoid 429)."""
  global _price_cache
  now = time.time()
  if _price_cache is not None and (now - _price_cache[1]) < _CACHE_SECONDS:
    return _price_cache[0]
  last_err = None
  for attempt in range(_MAX_RETRIES):
    try:
      resp = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": "bitcoin", "vs_currencies": "usd"},
        timeout=5
      )
      resp.raise_for_status()
      price = float(resp.json()["bitcoin"]["usd"])
      _price_cache = (price, now)
      logger.debug(f"BTC price: ${price:,.2f}")
      return price
    except requests.exceptions.RequestException as e:
      last_err = e
      if attempt < _MAX_RETRIES - 1:
        time.sleep(_RETRY_DELAY)
    except Exception as e:
      logger.error(f"Error fetching BTC price: {e}")
      if _price_cache is not None:
        return _price_cache[0]
      return None
  if _price_cache is not None:
    logger.warning(f"BTC price fetch failed (using cache): {last_err}")
    return _price_cache[0]
  logger.warning(f"BTC price unavailable (network/DNS): {last_err}")
  return None


def get_btc_price_at_timestamp(ts: int) -> Optional[float]:
  """
  BTC price at a Unix timestamp (e.g. 5min window start).
  Uses Binance 1m kline open so it matches resolution-style pricing.
  """
  if ts <= 0:
    return None
  start_ms = (ts // 60) * 60 * 1000
  try:
    resp = requests.get(
      "https://api.binance.com/api/v3/klines",
      params={"symbol": "BTCUSDT", "interval": "1m", "startTime": start_ms, "limit": 1},
      timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data or not data[0]:
      return None
    return float(data[0][1])
  except Exception as e:
    logger.debug(f"Historical BTC price at {ts}: {e}")
    return None
