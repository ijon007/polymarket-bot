"""Neon PostgreSQL connection and table creation."""

from datetime import datetime
from typing import Any, Optional

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.models import Base, Market as MarketModel, Opportunity, Trade
from src.utils.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    """Return a new database session."""
    return SessionLocal()


def create_all_tables():
    """Create all tables defined in models."""
    Base.metadata.create_all(bind=engine)


def save_market(market: Any) -> None:
    """Persist a market snapshot (Market dataclass or dict) to the database."""
    session = get_session()
    try:
        if hasattr(market, "ticker"):
            ticker = market.ticker
            title = getattr(market, "title", None)
            yes_price = getattr(market, "yes_price", None)
            no_price = getattr(market, "no_price", None)
            volume = getattr(market, "volume_24h", None) or getattr(market, "volume", None)
            category = getattr(market, "category", None)
        else:
            ticker = market.get("ticker")
            title = market.get("title")
            yes_price = market.get("yes_price")
            no_price = market.get("no_price")
            volume = market.get("volume_24h") or market.get("volume")
            category = market.get("category")
        row = MarketModel(
            ticker=ticker,
            title=title,
            yes_price=yes_price,
            no_price=no_price,
            volume=volume,
            category=category,
            fetched_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving market: {e}")
        raise
    finally:
        session.close()


def save_trade(trade: dict) -> None:
    """Insert a trade record."""
    session = get_session()
    try:
        row = Trade(
            market_ticker=trade["market_ticker"],
            side=trade["side"],
            price=trade["price"],
            size=trade["size"],
            reason=trade.get("reason"),
            expected_profit=trade.get("expected_profit"),
            executed_at=trade.get("executed_at") or datetime.utcnow(),
            status=trade.get("status", "paper"),
        )
        session.add(row)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving trade: {e}")
        raise
    finally:
        session.close()


def save_opportunity(
    market_ticker: str,
    type_: str,
    edge: Optional[float] = None,
    confidence: Optional[float] = None,
) -> None:
    """Insert an opportunity record."""
    session = get_session()
    try:
        row = Opportunity(
            market_ticker=market_ticker,
            type=type_,
            edge=edge,
            confidence=confidence,
            detected_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving opportunity: {e}")
        raise
    finally:
        session.close()
