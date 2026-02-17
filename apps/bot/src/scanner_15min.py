"""15-min BTC market fetcher. Used only by the 15-min signal engine (main_15min.py)."""
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from loguru import logger

from src.utils.price_feed import get_btc_price_at_timestamp

GAMMA_API = "https://gamma-api.polymarket.com"
_REQUEST_RETRIES = 5
_REQUEST_RETRY_DELAY = 3
_DNS_RETRY_DELAY = 8
_WINDOW_SECONDS = 900  # 15 min


def fetch_btc_15min_market() -> Optional[Dict[str, Any]]:
  """
  Fetch the current active 15-min BTC up/down market from Gamma API.
  Returns market dict with slug, condition_id, tokens, end_date, etc. or None.
  """
  now = datetime.now(timezone.utc)
  timestamp = int(now.timestamp())
  # 15-min windows: align to 900s boundaries
  base_ts = (timestamp // _WINDOW_SECONDS) * _WINDOW_SECONDS

  for i in range(-2, 5):
    window_ts = base_ts + (i * _WINDOW_SECONDS)
    slug = f"btc-updown-15m-{window_ts}"

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
        continue

      if resp.status_code != 200:
        continue

      data = resp.json()
      if not data or len(data) == 0:
        continue

      event = data[0]
      markets = event.get("markets", [])
      if not markets:
        continue

      market = markets[0]

      if market.get("closed"):
        continue

      end_date_str = market.get("endDateIso")
      if not end_date_str:
        logger.debug(f"No endDateIso for {slug}")
        continue

      try:
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
      except Exception:
        logger.debug(f"Failed to parse date: {end_date_str}")
        continue

      if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

      end_date_from_slug = datetime.fromtimestamp(
        window_ts + _WINDOW_SECONDS, tz=timezone.utc
      )
      if end_date <= now or (end_date.hour == 0 and end_date.minute == 0):
        end_date = end_date_from_slug

      seconds_left = (end_date - now).total_seconds()

      if seconds_left <= 0:
        continue

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
        continue

      yes_price = float(prices[0])
      no_price = float(prices[1])

      clob_ids = market.get("clobTokenIds", "")
      token_ids: Dict[str, str] = {}
      if clob_ids:
        ids = clob_ids.split(",") if isinstance(clob_ids, str) else clob_ids
        if len(ids) >= 2:
          token_ids["yes"] = ids[0].strip()
          token_ids["no"] = ids[1].strip()

      start_price = get_btc_price_at_timestamp(window_ts)
      price_to_beat = f"${start_price:,.2f}" if start_price is not None else "N/A"
      logger.info(
        f"15min ACTIVE: {slug} | YES: {yes_price}, NO: {no_price} | "
        f"Start: {price_to_beat} | {seconds_left:.0f}s left"
      )

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
        "resolution_source": market.get("resolutionSource")
        or event.get("resolutionSource")
        or "",
      }

    except Exception as e:
      logger.error(f"Error processing {slug}: {e}")
      continue

  return None
