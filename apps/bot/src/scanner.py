import json
import time
import requests
from datetime import datetime, timezone
from loguru import logger

from src.utils.price_feed import get_price_at_timestamp
from src.config import FIVE_MIN_ASSETS

GAMMA_API = "https://gamma-api.polymarket.com"
_REQUEST_RETRIES = 5
_REQUEST_RETRY_DELAY = 3
_DNS_RETRY_DELAY = 8  # longer wait when DNS fails (give network time to recover)


def fetch_5min_market(asset: str):
  """Fetch current active 5-min up/down market for one asset (btc/eth/sol/xrp). Returns market dict or None."""
  now = datetime.now(timezone.utc)
  timestamp = int(now.timestamp())
  a = (asset or "btc").strip().lower()

  for i in range(-2, 5):
    window_ts = (timestamp // 300 * 300) + (i * 300)
    slug = f"{a}-updown-5m-{window_ts}"

    try:
      last_err = None
      for attempt in range(_REQUEST_RETRIES):
        try:
          resp = requests.get(f"{GAMMA_API}/events", params={"slug": slug}, timeout=10)
          break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, OSError) as e:
          last_err = e
          err_str = str(e).lower()
          is_dns = "getaddrinfo failed" in err_str or "11001" in err_str or "name or service not known" in err_str
          delay = _DNS_RETRY_DELAY if is_dns else _REQUEST_RETRY_DELAY
          if attempt < _REQUEST_RETRIES - 1:
            time.sleep(delay)
          continue
      else:
        err_str = str(last_err).lower() if last_err else ""
        if "getaddrinfo failed" in err_str or "11001" in err_str:
          logger.warning(f"gamma-api DNS failed after {_REQUEST_RETRIES} tries — check internet/DNS/VPN; retry next cycle")
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
      end_date_from_slug = datetime.fromtimestamp(window_ts + 300, tz=timezone.utc)
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
        prices = [float(p) for p in outcome_prices]
      if len(prices) < 2:
        continue

      yes_price = float(prices[0])
      no_price = float(prices[1])

      clob_ids = market.get("clobTokenIds", "")
      token_ids = {}
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

      start_price = get_price_at_timestamp(window_ts, a)
      return {
        "condition_id": market.get("conditionId"),
        "question": market.get("question"),
        "yes_price": yes_price,
        "no_price": no_price,
        "end_date": end_date,
        "tokens": token_ids,
        "seconds_left": int(seconds_left),
        "slug": slug,
        "window_start_ts": window_ts,
        "resolution_source": market.get("resolutionSource") or event.get("resolutionSource") or "",
        "asset": a,
        "start_price": start_price,
      }

    except Exception as e:
      logger.error(f"Error processing {slug}: {e}")
      continue

  return None


def fetch_5min_markets():
  """Fetch all active 5-min markets for FIVE_MIN_ASSETS. Returns list (one per asset max)."""
  out = []
  by_asset = {}
  for asset in FIVE_MIN_ASSETS:
    m = fetch_5min_market(asset)
    if m:
      out.append(m)
      by_asset[asset] = m
  parts = []
  for asset in FIVE_MIN_ASSETS:
    m = by_asset.get(asset)
    if m:
      start_price = m.get("start_price")
      if start_price is not None:
        ptb = f"${start_price:,.4f}" if asset == "xrp" else f"${start_price:,.2f}"
      else:
        ptb = "N/A"
      parts.append(
        f"{asset} {m['yes_price']:.4g}/{m['no_price']:.4g} {ptb} {m.get('seconds_left', 0)}s"
      )
    else:
      parts.append(f"{asset} -")
  logger.info("ACTIVE: " + " | ".join(parts))
  return out


def fetch_btc_5min_market():
  """Backward compat: fetch current BTC 5-min market only."""
  return fetch_5min_market("btc")


def fetch_btc_5min_markets():
  """Backward compat: returns list of BTC 5-min markets only."""
  return [m for m in fetch_5min_markets() if m.get("asset") == "btc"]
