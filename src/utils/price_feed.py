import requests
from loguru import logger
from typing import Optional


def get_btc_price() -> Optional[float]:
    """Fetch current BTC price from CoinGecko"""
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=5
        )
        resp.raise_for_status()
        price = resp.json()["bitcoin"]["usd"]
        logger.debug(f"BTC price: ${price:,.2f}")
        return float(price)
    except Exception as e:
        logger.error(f"Error fetching BTC price: {e}")
        return None
