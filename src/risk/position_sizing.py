"""Position sizing via Kelly criterion with confidence and trade-type caps."""

from src.utils.config import (
    MAX_POSITION_SIZE,
    MAX_POSITION_SIZE_ARB,
    MAX_POSITION_SIZE_LOGIC,
)


def calculate_position_size(
    edge: float,
    confidence: float,
    bankroll: float,
    trade_type: str,
    implied_prob: float = 0.5,
) -> float:
    """
    Kelly-based size with quarter-Kelly and confidence scaling. Capped by trade_type.

    - logic: max 10% bankroll
    - internal_arb: max 15%
    - else: max 5%
    """
    if bankroll <= 0 or confidence <= 0:
        return 0.0
    if implied_prob >= 1.0:
        implied_prob = 0.99
    kelly = edge / (1.0 - implied_prob) if implied_prob < 1.0 else 0.0
    adjusted_kelly = kelly * confidence
    size = bankroll * adjusted_kelly * 0.25

    if trade_type == "logic":
        max_size = bankroll * MAX_POSITION_SIZE_LOGIC
    elif trade_type == "internal_arb":
        max_size = bankroll * MAX_POSITION_SIZE_ARB
    else:
        max_size = bankroll * MAX_POSITION_SIZE

    return min(max(size, 0.0), max_size)
