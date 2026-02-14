"""Fair value from base rate and consensus (no ML)."""

from typing import Any

from src.analysis.base_rates import get_base_rate


def calculate_fair_value(market: Any) -> float:
    """
    Two-source fair value: 50% base rate + 50% current market consensus.

    If base_rate is unavailable, returns consensus (market price). Used to validate
    that arbitrage opportunities are not based on misinformation.
    """
    base_rate = get_base_rate(market)
    yes_price = getattr(market, "yes_price", None) or (market.get("yes_price") if isinstance(market, dict) else None)
    if yes_price is None:
        return 0.0
    # Support both cents (0–100) and decimal (0–1)
    consensus = float(yes_price) / 100.0 if float(yes_price) > 1 else float(yes_price)

    if base_rate is not None:
        return 0.5 * base_rate + 0.5 * consensus
    return consensus
