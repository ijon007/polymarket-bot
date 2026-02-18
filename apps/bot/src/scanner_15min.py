"""15-min crypto market fetcher. Used by the 15-min signal engine (main_15min.py)."""
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import requests
from loguru import logger

from src.config import LATE_ENTRY_15MIN_ASSETS
from src.utils.price_feed import (
  get_btc_price_at_timestamp,
  get_eth_price_at_timestamp,
  get_sol_price_at_timestamp,
  get_xrp_price_at_timestamp,
)

_START_PRICE_FNS = {
  "btc": get_btc_price_at_timestamp,
  "eth": get_eth_price_at_timestamp,
  "sol": get_sol_price_at_timestamp,
  "xrp": get_xrp_price_at_timestamp,
}

GAMMA_API = "https://gamma-api.polymarket.com"
_REQUEST_RETRIES = 5
_REQUEST_RETRY_DELAY = 3
_DNS_RETRY_DELAY = 8
_WINDOW_SECONDS = 900  # 15 min


def _fetch_one_market(slug: str, asset: str, window_ts: int, now: datetime) -> Optional[Dict[str, Any]]:
  """Fetch and parse one 15-min market by slug. Returns market dict or None."""
  try:
    last_err = None
    for attempt in range(_REQUEST_RETRIES):
      try:
        resp = requests.get(
          f"{GAMMA_API}/events",
          params={"slug": slug},
          timeout=10,
        )
        break
      except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        OSError,
      ) as e:
        last_err = e
        err_str = str(e).lower()
        is_dns = (
          "getaddrinfo failed" in err_str
          or "11001" in err_str
          or "name or service not known" in err_str
        )
        delay = _DNS_RETRY_DELAY if is_dns else _REQUEST_RETRY_DELAY
        if attempt < _REQUEST_RETRIES - 1:
          time.sleep(delay)
        continue
    else:
      err_str = str(last_err).lower() if last_err else ""
      if "getaddrinfo failed" in err_str or "11001" in err_str:
        logger.warning(
          f"gamma-api.polymarket.com failed to resolve (DNS) for {slug} — "
          "check internet, DNS, or VPN"
        )
      else:
        logger.warning(f"Network error for {slug} after {_REQUEST_RETRIES} tries: {last_err}")
      return None

    if resp.status_code != 200:
      return None

    data = resp.json()
    if not data or len(data) == 0:
      return None

    event = data[0]
    markets = event.get("markets", [])
    if not markets:
      return None

    market = markets[0]

    if market.get("closed"):
      return None

    end_date_str = market.get("endDateIso")
    if not end_date_str:
      logger.debug(f"No endDateIso for {slug}")
      return None

    try:
      end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
    except Exception:
      logger.debug(f"Failed to parse date: {end_date_str}")
      return None

    if end_date.tzinfo is None:
      end_date = end_date.replace(tzinfo=timezone.utc)

    end_date_from_slug = datetime.fromtimestamp(
      window_ts + _WINDOW_SECONDS, tz=timezone.utc
    )
    if end_date <= now or (end_date.hour == 0 and end_date.minute == 0):
      end_date = end_date_from_slug

    seconds_left = (end_date - now).total_seconds()

    if seconds_left <= 0:
      return None

    outcome_prices = market.get("outcomePrices", [])
    if isinstance(outcome_prices, str):
      s = outcome_prices.strip()
      if s.startswith("["):
        prices = [float(x) for x in json.loads(s)]
      else:
        prices = [float(p.strip()) for p in s.split(",")]
    else:
      prices = [float(p) for p in outcome_prices] if outcome_prices else []

    if len(prices) < 2:
      return None

    yes_price = float(prices[0])
    no_price = float(prices[1])

    clob_ids = market.get("clobTokenIds", "")
    token_ids: Dict[str, str] = {}
    if clob_ids:
      if isinstance(clob_ids, list) and len(clob_ids) >= 2:
        ids = [str(x).strip() for x in clob_ids[:2]]
      elif isinstance(clob_ids, str):
        s = clob_ids.strip()
        if s.startswith("["):
          try:
            parsed = json.loads(s)
            ids = [str(x).strip() for x in parsed[:2]] if isinstance(parsed, list) else []
          except (json.JSONDecodeError, TypeError):
            ids = [x.strip().strip('"') for x in s.split(",")][:2]
        else:
          ids = [x.strip().strip('"') for x in s.split(",")][:2]
      else:
        ids = []
      if len(ids) >= 2:
        token_ids["yes"] = ids[0]
        token_ids["no"] = ids[1]

    if not token_ids:
      return None

    start_price = _START_PRICE_FNS.get(asset, lambda _: None)(window_ts)

    return {
      "condition_id": market.get("conditionId") or "",
      "question": market.get("question") or "",
      "yes_price": yes_price,
      "no_price": no_price,
      "end_date": end_date,
      "tokens": token_ids,
      "seconds_left": int(seconds_left),
      "slug": slug,
      "window_start_ts": window_ts,
      "start_price": start_price,
      "resolution_source": market.get("resolutionSource")
      or event.get("resolutionSource")
      or "",
    }

  except Exception as e:
    logger.error(f"Error processing {slug}: {e}")
    return None


def fetch_15min_markets(
  assets: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
  """
  Fetch all active 15-min up/down markets for the given assets.
  Returns list of market dicts (slug, tokens, end_date, etc.) for the first
  window that has at least one active market. All returned markets share the same window.
  """
  assets = assets or LATE_ENTRY_15MIN_ASSETS
  now = datetime.now(timezone.utc)
  timestamp = int(now.timestamp())
  base_ts = (timestamp // _WINDOW_SECONDS) * _WINDOW_SECONDS

  for i in range(-2, 5):
    window_ts = base_ts + (i * _WINDOW_SECONDS)
    result: List[Dict[str, Any]] = []
    for asset in assets:
      slug = f"{asset}-updown-15m-{window_ts}"
      m = _fetch_one_market(slug, asset, window_ts, now)
      if m:
        result.append(m)
    if result:
      sec_left = result[0].get("seconds_left", 0)
      slugs = [m.get("slug", "") for m in result]
      start_summary = ", ".join(
        f"{m.get('slug', '').split('-')[0]}: ${m['start_price']:,.2f}" if m.get("start_price") is not None
        else f"{m.get('slug', '').split('-')[0]}: N/A"
        for m in result
      )
      logger.info(
        f"15min ACTIVE: {', '.join(slugs)} | Start: {start_summary} | {sec_left}s left"
      )
      return result

  return []


def fetch_btc_15min_market() -> Optional[Dict[str, Any]]:
  """
  Fetch the current active 15-min BTC up/down market from Gamma API.
  Returns market dict with slug, condition_id, tokens, end_date, etc. or None.
  Backward compat: uses fetch_15min_markets(assets=["btc"]) and returns first.
  """
  markets = fetch_15min_markets(assets=["btc"])
  return markets[0] if markets else None
