"""Portfolio limits and position management (stop loss, take profit)."""

from loguru import logger

from src.data.database import get_session
from src.data.models import Position
from src.utils.config import (
    BANKROLL,
    MAX_CATEGORY_EXPOSURE,
    MAX_OPEN_POSITIONS,
    MAX_TOTAL_EXPOSURE,
    STOP_LOSS,
    TAKE_PROFIT,
)


def check_limits() -> bool:
    """
    Before each trade: total_exposure < 40%, category_exposure < 15%, open_positions < 10.
    Returns True if within limits.
    """
    if BANKROLL <= 0:
        return False
    session = get_session()
    try:
        open_positions = (
            session.query(Position)
            .filter(Position.status == "open")
            .all()
        )
        count = len(open_positions)
        if count >= MAX_OPEN_POSITIONS:
            logger.debug(f"At max open positions: {count} >= {MAX_OPEN_POSITIONS}")
            return False

        total_exposure = 0.0
        category_exposure: dict[str, float] = {}
        for p in open_positions:
            exp = (p.entry_price or 0) * (p.size or 0)
            total_exposure += exp
            cat = p.market_ticker[:20] if p.market_ticker else "default"
            category_exposure[cat] = category_exposure.get(cat, 0) + exp

        if total_exposure / BANKROLL >= MAX_TOTAL_EXPOSURE:
            logger.debug(f"Total exposure limit: {total_exposure / BANKROLL:.2%} >= {MAX_TOTAL_EXPOSURE:.0%}")
            return False
        for cat, exp in category_exposure.items():
            if exp / BANKROLL >= MAX_CATEGORY_EXPOSURE:
                logger.debug(f"Category exposure limit: {cat} {exp / BANKROLL:.2%} >= {MAX_CATEGORY_EXPOSURE:.0%}")
                return False
        return True
    finally:
        session.close()


def manage_positions() -> None:
    """
    For each open position: apply stop loss -25%, take profit +50%, or close if edge flips.
    Updates Position status in DB.
    """
    session = get_session()
    try:
        open_positions = session.query(Position).filter(Position.status == "open").all()
        for p in open_positions:
            current = p.current_price if p.current_price is not None else p.entry_price
            if current is None or p.entry_price is None or p.entry_price == 0:
                continue
            pnl_pct = (current - p.entry_price) / p.entry_price
            if pnl_pct <= STOP_LOSS:
                p.status = "closed"
                p.pnl = (current - p.entry_price) * (p.size or 0)
                logger.info(f"Stop loss: closed {p.market_ticker} at {pnl_pct:.2%}")
            elif pnl_pct >= TAKE_PROFIT:
                p.status = "closed"
                p.pnl = (current - p.entry_price) * (p.size or 0)
                logger.info(f"Take profit: closed {p.market_ticker} at {pnl_pct:.2%}")
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error managing positions: {e}")
    finally:
        session.close()
