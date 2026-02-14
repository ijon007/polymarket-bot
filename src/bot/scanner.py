"""Market scanning: fetch active markets from Polymarket CLOB and persist to Neon."""

import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.bot.bot_types import Market
from src.data.database import save_markets_batch
from src.utils.config import MIN_LIQUIDITY, QUICK_MARKET_MAX_SECONDS


def _parse_markets_response(response: Any) -> List[dict]:
    """Return list of market dicts from API response (list or paginated)."""
    if isinstance(response, list):
        return response
    if hasattr(response, "data"):
        return getattr(response, "data", []) or []
    if isinstance(response, dict) and "data" in response:
        return response["data"] or []
    return []


def _extract_tokens(raw: dict) -> tuple[float, float, dict]:
    """Extract yes_price, no_price (0-1), and tokens dict with yes/no token_ids."""
    yes_price, no_price = 0.0, 0.0
    tokens_out = {}
    tokens = raw.get("tokens") or raw.get("outcomes") or []
    for t in tokens:
        tid = t.get("token_id") or t.get("id")
        outcome = (t.get("outcome") or t.get("name") or "").upper()
        price = t.get("price")
        if price is not None:
            p = float(price)
            if p > 1:
                p = p / 100.0
            if "YES" in outcome or outcome == "Y":
                yes_price = p
                tokens_out["yes"] = tid
            elif "NO" in outcome or outcome == "N":
                no_price = p
                tokens_out["no"] = tid
    return yes_price, no_price, tokens_out


def _parse_end_date_iso(raw: dict) -> Optional[datetime]:
    """Parse end_date_iso or endDate from raw market dict; return timezone-aware datetime or None."""
    s = raw.get("end_date_iso") or raw.get("endDate")
    if not s:
        return None
    try:
        s = str(s).strip().replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _get_order_book_info(client: Any, token_id: str) -> tuple[float, float]:
    """Return (best_ask, depth_usd) for token. Depth is sum of ask sizes * prices."""
    try:
        book = client.get_order_book(token_id)
        if not book:
            return 0.0, 0.0
        asks = book.get("asks", []) if isinstance(book, dict) else []
        if not asks:
            return 0.0, 0.0
        best_ask = float(asks[0].get("price", 0)) if asks else 0.0
        if best_ask > 1:
            best_ask = best_ask / 100.0
        depth = sum(float(a.get("size", 0) or 0) * float(a.get("price", 0) or 0) / 100.0 for a in asks[:10])
        return best_ask, depth
    except Exception as e:
        # 404 = no orderbook for this token (expected for some markets); skip log
        if getattr(e, "status_code", None) != 404 and "No orderbook" not in str(e):
            logging.getLogger(__name__).debug("Order book fetch failed for %s: %s", str(token_id)[:20], e)
        return 0.0, 0.0


def fetch_markets() -> List[Market]:
    """
    Fetch active markets from Polymarket CLOB, enrich with order book, save to Neon.

    Returns list of Market dataclasses with prices in decimal 0-1. Skips inactive,
    resolved, expired, and low-volume (< MIN_LIQUIDITY) markets.
    """
    from py_clob_client.client import ClobClient

    try:
        client = ClobClient(host="https://clob.polymarket.com", chain_id=137)
        raw_list = client.get_markets(limit=1000)
        markets_data = _parse_markets_response(raw_list)
    except Exception as e:
        logging.getLogger(__name__).error("Error fetching markets: %s", e)
        return []

    now_utc = datetime.now(timezone.utc)
    active_markets: List[Market] = []
    for raw in markets_data:
        try:
            if raw.get("closed"):
                continue
            end_date = _parse_end_date_iso(raw)
            if not end_date or end_date <= now_utc:
                continue
            vol = raw.get("volume_24h") or raw.get("volume") or raw.get("volumeNum") or 0
            try:
                vol = float(vol)
            except (TypeError, ValueError):
                vol = 0.0
            if vol < MIN_LIQUIDITY:
                continue

            ticker = raw.get("condition_id") or raw.get("id") or raw.get("market_slug") or ""
            if not ticker:
                continue
            title = raw.get("question") or raw.get("title") or raw.get("description") or ""
            description = raw.get("description") or title
            yes_price, no_price, tokens = _extract_tokens(raw)

            best_yes_ask = yes_price
            best_no_ask = no_price
            depth_yes = 0.0
            depth_no = 0.0
            if tokens.get("yes"):
                best_yes_ask, depth_yes = _get_order_book_info(client, tokens["yes"])
                if best_yes_ask <= 0:
                    best_yes_ask = yes_price
            if tokens.get("no"):
                best_no_ask, depth_no = _get_order_book_info(client, tokens["no"])
                if best_no_ask <= 0:
                    best_no_ask = no_price

            spread = abs(best_yes_ask - (1.0 - best_no_ask)) if (best_yes_ask and best_no_ask) else 0.0

            market = Market(
                ticker=ticker,
                title=title,
                yes_price=yes_price,
                no_price=no_price,
                best_yes_ask=best_yes_ask or yes_price,
                best_no_ask=best_no_ask or no_price,
                volume_24h=vol,
                spread=spread,
                resolution_criteria=description,
                tokens=tokens or None,
                category=raw.get("category") or raw.get("group") or None,
                slug=raw.get("market_slug"),
                depth_yes=depth_yes,
                depth_no=depth_no,
                end_date=end_date,
            )
            active_markets.append(market)
        except Exception as e:
            logging.getLogger(__name__).debug("Skip market %s: %s", raw.get('condition_id', raw.get('id')), e)
            continue

    if active_markets:
        save_markets_batch(active_markets)
    logging.getLogger(__name__).info("Scanned %d active markets", len(active_markets))
    return active_markets


def fetch_quick_markets() -> List[Market]:
    """
    Fetch markets ending soon (< QUICK_MARKET_MAX_SECONDS). Uses get_markets() for end_date_iso.
    Returns list of Market instances with end_date set, filtered to those closing within the window.
    """
    from py_clob_client.client import ClobClient  # type: ignore[import-untyped]

    try:
        client = ClobClient(host="https://clob.polymarket.com", chain_id=137)
        raw_list = client.get_markets(limit=1000)
        markets_data = _parse_markets_response(raw_list)
    except Exception as e:
        logging.getLogger(__name__).error("Error fetching markets for quick scan: %s", e)
        return []

    now_utc = datetime.now(timezone.utc)
    quick_markets: List[Market] = []

    for raw in markets_data:
        try:
            if raw.get("closed"):
                continue
            end_date = _parse_end_date_iso(raw)
            if end_date is None:
                continue
            seconds_left = (end_date - now_utc).total_seconds()
            if seconds_left <= 0 or seconds_left > QUICK_MARKET_MAX_SECONDS:
                continue

            vol = raw.get("volume_24h") or raw.get("volume") or raw.get("volumeNum") or 0
            try:
                vol = float(vol)
            except (TypeError, ValueError):
                vol = 0.0

            ticker = raw.get("condition_id") or raw.get("id") or raw.get("market_slug") or ""
            if not ticker:
                continue
            title = raw.get("question") or raw.get("title") or raw.get("description") or ""
            description = raw.get("description") or title
            yes_price, no_price, tokens = _extract_tokens(raw)

            best_yes_ask = yes_price
            best_no_ask = no_price
            depth_yes = 0.0
            depth_no = 0.0
            if tokens.get("yes"):
                best_yes_ask, depth_yes = _get_order_book_info(client, tokens["yes"])
                if best_yes_ask <= 0:
                    best_yes_ask = yes_price
            if tokens.get("no"):
                best_no_ask, depth_no = _get_order_book_info(client, tokens["no"])
                if best_no_ask <= 0:
                    best_no_ask = no_price

            spread = abs(best_yes_ask - (1.0 - best_no_ask)) if (best_yes_ask and best_no_ask) else 0.0

            market = Market(
                ticker=ticker,
                title=title,
                yes_price=yes_price,
                no_price=no_price,
                best_yes_ask=best_yes_ask or yes_price,
                best_no_ask=best_no_ask or no_price,
                volume_24h=vol,
                spread=spread,
                resolution_criteria=description,
                tokens=tokens or None,
                category=raw.get("category") or raw.get("group") or None,
                slug=raw.get("market_slug"),
                depth_yes=depth_yes,
                depth_no=depth_no,
                end_date=end_date,
            )
            quick_markets.append(market)
        except Exception as e:
            logging.getLogger(__name__).debug("Skip quick market %s: %s", raw.get("condition_id", raw.get("id")), e)
            continue

    logging.getLogger(__name__).info("Quick markets (ending in < %ds): %d", QUICK_MARKET_MAX_SECONDS, len(quick_markets))
    return quick_markets
