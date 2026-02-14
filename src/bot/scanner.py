"""Market scanning: fetch active markets from Polymarket CLOB and persist to Neon."""

from typing import Any, List

from loguru import logger

from src.bot.types import Market
from src.data.database import save_market
from src.utils.config import MIN_LIQUIDITY


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
        logger.debug(f"Order book fetch failed for {token_id}: {e}")
        return 0.0, 0.0


def fetch_markets() -> List[Market]:
    """
    Fetch active markets from Polymarket CLOB, enrich with order book, save to Neon.

    Returns list of Market dataclasses with prices in decimal 0-1. Filters by active
    and volume >= MIN_LIQUIDITY when volume is available.
    """
    from py_clob_client.client import ClobClient

    try:
        client = ClobClient(host="https://clob.polymarket.com", chain_id=137)
        try:
            raw_list = client.get_markets(limit=1000)
        except TypeError:
            raw_list = client.get_markets()
        markets_data = _parse_markets_response(raw_list)
    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []

    active_markets: List[Market] = []
    for raw in markets_data:
        try:
            if not raw.get("active", True):
                continue
            vol = raw.get("volume_24h") or raw.get("volume") or raw.get("volumeNum") or 0
            try:
                vol = float(vol)
            except (TypeError, ValueError):
                vol = 0.0
            if vol < MIN_LIQUIDITY and vol > 0:
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
            )
            save_market(market)
            active_markets.append(market)
        except Exception as e:
            logger.debug(f"Skip market {raw.get('condition_id', raw.get('id'))}: {e}")
            continue

    logger.info(f"Scanned {len(active_markets)} active markets")
    return active_markets
