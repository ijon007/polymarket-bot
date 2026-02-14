import requests
from datetime import datetime, timezone
from loguru import logger

GAMMA_API = "https://gamma-api.polymarket.com"


def fetch_btc_5min_markets():
  """
  Fetch ONLY BTC 5-minute up/down markets.

  Returns list of dicts with:
  - condition_id (ticker)
  - question (title)
  - yes_price (0-1)
  - no_price (0-1)
  - end_date (datetime)
  - tokens (dict with yes/no token_ids)
  """
  try:
    resp = requests.get(
      f"{GAMMA_API}/markets",
      params={"closed": "false", "limit": 200},
      timeout=15,
    )
    resp.raise_for_status()
    all_markets = resp.json() if isinstance(resp.json(), list) else []

    btc_markets = []
    now = datetime.now(timezone.utc)

    for m in all_markets:
      # Filter: BTC markets only
      title = (m.get("question") or "").lower()
      if "btc" not in title and "bitcoin" not in title:
        continue

      # Filter: 5min markets only (check title contains "5m" or "5 min")
      if "5m" not in title and "5 min" not in title:
        continue

      # Filter: Must be accepting orders
      if not m.get("acceptingOrders", True):
        continue

      # Filter: Must have order book enabled
      if not m.get("enableOrderBook", True):
        continue

      # Parse end date
      end_date_str = m.get("endDateIso") or m.get("endDate")
      if not end_date_str:
        continue

      try:
        end_date = datetime.fromisoformat(
          str(end_date_str).replace("Z", "+00:00")
        )
      except (ValueError, TypeError):
        continue

      # Filter: Must end in next 10 minutes (active 5min market)
      seconds_left = (end_date - now).total_seconds()
      if seconds_left < 0 or seconds_left > 600:
        continue

      # Extract YES/NO prices from outcomePrices (e.g. "0.45,0.55")
      outcome_prices = m.get("outcomePrices") or m.get("outcomePricesNum")
      if outcome_prices is None:
        continue

      if isinstance(outcome_prices, str):
        prices = [float(p.strip()) for p in outcome_prices.split(",")]
      else:
        prices = [float(p) for p in outcome_prices]

      if len(prices) < 2:
        continue

      # outcomePrices order: typically [YES/UP, NO/DOWN]
      yes_price = float(prices[0])
      no_price = float(prices[1])

      # Normalize if prices are 0-100
      if yes_price > 1:
        yes_price = yes_price / 100.0
      if no_price > 1:
        no_price = no_price / 100.0

      # Get token IDs
      clob_ids = m.get("clobTokenIds") or ""
      token_ids = {}
      if clob_ids:
        ids = clob_ids.split(",") if isinstance(clob_ids, str) else clob_ids
        if len(ids) >= 2:
          token_ids["yes"] = ids[0].strip()
          token_ids["no"] = ids[1].strip()

      # Skip if prices missing
      if yes_price <= 0 or no_price <= 0:
        continue

      btc_markets.append({
        "condition_id": m.get("conditionId") or m.get("condition_id"),
        "question": m.get("question"),
        "yes_price": yes_price,
        "no_price": no_price,
        "end_date": end_date,
        "tokens": token_ids,
        "seconds_left": int(seconds_left),
      })

    logger.info(f"Found {len(btc_markets)} active BTC 5min markets")
    return btc_markets

  except Exception as e:
    logger.error(f"Error fetching markets: {e}")
    return []
