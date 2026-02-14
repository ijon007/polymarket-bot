"""Internal and combinatorial arbitrage detection."""

import json
import re
from typing import Any, List, Optional

from loguru import logger

from src.bot.types import Market
from src.utils.config import GROQ_API_KEY

MIN_PROFIT_INTERNAL = 0.03  # 3% minimum (total < 0.97)
MIN_DEPTH_USD = 100.0
MAX_SPREAD_INTERNAL = 0.05
MIN_VOLUME_INTERNAL = 10000
COMBO_SUM_THRESHOLD = 0.95  # sum of YES prices < 0.95 for arb


def find_internal_arb(market: Any) -> Optional[dict]:
    """
    If yes_ask + no_ask < 0.97 (3% min profit), volume > 10k, spread < 5¢, depth >= $100 each side,
    return arb dict; else None.
    """
    best_yes = getattr(market, "best_yes_ask", None) or getattr(market, "yes_price", 0) or 0
    best_no = getattr(market, "best_no_ask", None) or getattr(market, "no_price", 0) or 0
    if best_yes > 1:
        best_yes = best_yes / 100.0
    if best_no > 1:
        best_no = best_no / 100.0
    total_cost = best_yes + best_no
    if total_cost >= 0.97:
        return None
    if getattr(market, "volume_24h", 0) or 0 < MIN_VOLUME_INTERNAL:
        return None
    spread = getattr(market, "spread", 1.0) or 1.0
    if spread > MAX_SPREAD_INTERNAL:
        return None
    depth_yes = getattr(market, "depth_yes", 0) or 0
    depth_no = getattr(market, "depth_no", 0) or 0
    if depth_yes < MIN_DEPTH_USD or depth_no < MIN_DEPTH_USD:
        return None

    profit = 1.00 - total_cost
    profit_pct = (profit / total_cost) * 100.0
    return {
        "action": "internal_arb",
        "yes_price": best_yes,
        "no_price": best_no,
        "total_cost": total_cost,
        "expected_profit": profit,
        "profit_pct": profit_pct,
        "confidence": 0.99,
    }


def extract_event_id(market: Any) -> str:
    """Derive a group key from ticker/slug/category so related markets share the same id."""
    slug = getattr(market, "slug", None) or getattr(market, "market_slug", None)
    if slug:
        # e.g. "election-2024-president" -> "election-2024"
        parts = str(slug).split("-")
        if len(parts) >= 2:
            return "-".join(parts[:2])
        return str(slug)
    ticker = getattr(market, "ticker", "") or ""
    if ticker:
        # condition_id often has structure; use first part or full
        return ticker[:32] if len(ticker) > 32 else ticker
    category = getattr(market, "category", None) or ""
    return str(category) or "unknown"


def _llm_mutually_exclusive(markets: List[Any]) -> Optional[dict]:
    """Ask Groq whether markets are mutually exclusive; return parsed JSON or None."""
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        lines = []
        for m in markets:
            title = getattr(m, "title", "") or ""
            y = getattr(m, "yes_price", 0) or 0
            if y > 1:
                y = y / 100.0
            lines.append(f"- {title} (YES: {y * 100:.1f}¢)")
        current_sum = sum(getattr(m, "yes_price", 0) or 0 for m in markets)
        if any((getattr(m, "yes_price", 0) or 0) > 1 for m in markets):
            current_sum = current_sum / 100.0
        prompt = f"""Are these markets mutually exclusive (only one can happen)?
Markets:
{"\n".join(lines)}

Questions:
Are these mutually exclusive? (yes/no)
Should their probabilities sum to 100%? (yes/no)
Current sum: {current_sum * 100:.1f}¢
Is there an arbitrage opportunity? (yes/no)

Output JSON only: {{"mutually_exclusive": bool, "should_sum_to_100": bool, "has_arbitrage": bool, "reasoning": str}}"""

        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.debug(f"LLM mutually exclusive check failed: {e}")
    return None


def find_combinatorial_arb(markets: List[Any]) -> Optional[dict]:
    """
    For one group of related markets, check if mutually exclusive and sum(YES) < 0.95.
    Return arb dict or None.
    """
    if len(markets) < 2:
        return None
    yes_prices = []
    for m in markets:
        y = getattr(m, "yes_price", 0) or 0
        if y > 1:
            y = y / 100.0
        yes_prices.append(y)
    total_cost = sum(yes_prices)
    if total_cost >= COMBO_SUM_THRESHOLD:
        return None

    llm = _llm_mutually_exclusive(markets)
    if llm and not llm.get("mutually_exclusive", False):
        return None

    profit = 1.00 - total_cost
    tickers = [getattr(m, "ticker", "") or "" for m in markets]
    return {
        "action": "combinatorial_arb",
        "markets": tickers,
        "prices": yes_prices,
        "total_cost": total_cost,
        "expected_profit": profit,
        "confidence": 0.95,
    }


def find_all_combinatorial_arbs(markets: List[Any]) -> List[dict]:
    """Group markets by extract_event_id, then run find_combinatorial_arb on each group."""
    groups: dict[str, List[Any]] = {}
    for m in markets:
        eid = extract_event_id(m)
        if eid not in groups:
            groups[eid] = []
        groups[eid].append(m)

    results: List[dict] = []
    for group in groups.values():
        if len(group) < 2:
            continue
        arb = find_combinatorial_arb(group)
        if arb:
            results.append(arb)
    return results
