"""Shared types for the bot (Market dataclass used by scanner, logic_filter, arbitrage)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Market:
    """Unified market representation from scanner for strategy layers."""

    ticker: str
    title: str
    yes_price: float
    no_price: float
    best_yes_ask: float
    best_no_ask: float
    volume_24h: float
    spread: float
    resolution_criteria: str
    tokens: Optional[dict] = None  # e.g. {"yes": token_id, "no": token_id}
    category: Optional[str] = None
    slug: Optional[str] = None
    depth_yes: float = 0.0  # order book depth in USD on YES side
    depth_no: float = 0.0   # order book depth in USD on NO side
