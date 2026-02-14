import time
import requests
from loguru import logger
from typing import Optional, Tuple

# Cache to avoid CoinGecko rate limit (429)
_CACHE_SECONDS = 15
_price_cache: Optional[Tuple[float, float]] = None  # (price, timestamp)


def get_btc_price() -> Optional[float]:
  """Fetch current BTC price from CoinGecko (cached 15s to avoid 429)."""
  global _price_cache
  now = time.time()
  if _price_cache is not None and (now - _price_cache[1]) < _CACHE_SECONDS:
    return _price_cache[0]
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
  except Exception as e:
    logger.error(f"Error fetching BTC price: {e}")
    if _price_cache is not None:
      return _price_cache[0]
    return None
