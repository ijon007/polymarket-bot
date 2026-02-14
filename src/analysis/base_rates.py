"""Historical frequency / base rate database for fair value and logic validation."""

from typing import Any, Optional

from src.data.database import get_session
from src.data.models import Market as MarketModel

# Seed with known patterns: impossible, certain, and historical examples
BASE_RATES: dict[str, Optional[float]] = {
    "jesus_return": 0.0,
    "aliens_confirmed": 0.0,
    "supernatural_event": 0.0,
    "sun_rise": 1.0,
    "earth_rotate": 1.0,
    "nfl_home_favorite": 0.58,
    "nfl_road_underdog": 0.42,
    "presidential_approval_above_60": 0.05,
    "bitcoin_new_ath": 0.15,
    "unknown": None,
}

# Keywords that map to base rate keys (lowercase for matching)
KEYWORD_TO_KEY: list[tuple[list[str], str]] = [
    (["jesus", "second coming", "messiah"], "jesus_return"),
    (["aliens", "ufo", "extraterrestrial", "first contact"], "aliens_confirmed"),
    (["supernatural", "miracle", "ghost", "paranormal"], "supernatural_event"),
    (["sun rise", "sunrise", "sun rises"], "sun_rise"),
    (["earth rotate", "earth rotation"], "earth_rotate"),
    (["nfl", "home favorite", "home team wins"], "nfl_home_favorite"),
    (["road underdog", "away underdog"], "nfl_road_underdog"),
    (["presidential approval", "approval above 60"], "presidential_approval_above_60"),
    (["bitcoin", "new ath", "all time high"], "bitcoin_new_ath"),
]


def get_base_rate(market: Any) -> Optional[float]:
    """
    Return a base rate (0.0–1.0) for the market from keyword match or historical DB.

    Tries keyword matching on market.title, then optionally queries Neon for similar
    historical markets. Returns None if no match.
    """
    title = (getattr(market, "title", None) or getattr(market, "resolution_criteria", None) or "") or ""
    if isinstance(market, dict):
        title = market.get("title") or market.get("resolution_criteria") or ""
    text = title.lower()

    for keywords, key in KEYWORD_TO_KEY:
        if any(kw in text for kw in keywords):
            rate = BASE_RATES.get(key)
            if rate is not None:
                return rate

    # Optional: query Neon for similar historical markets by category/title
    try:
        session = get_session()
        try:
            # Simple similarity: same category and we have historical yes_price mean
            category = getattr(market, "category", None) or (market.get("category") if isinstance(market, dict) else None)
            if category:
                from sqlalchemy import func

                result = (
                    session.query(func.avg(MarketModel.yes_price))
                    .filter(MarketModel.category == category, MarketModel.yes_price.isnot(None))
                    .scalar()
                )
                if result is not None:
                    return float(result) / 100.0 if result > 1 else float(result)
        finally:
            session.close()
    except Exception:
        pass

    return None
