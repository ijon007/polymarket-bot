"""SQLAlchemy declarative models for markets, trades, positions, and opportunities."""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Market(Base):
    """Market snapshot: ticker, prices, volume, category."""

    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(64), nullable=False, index=True)
    title = Column(Text, nullable=True)
    yes_price = Column(Float, nullable=True)
    no_price = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    category = Column(String(128), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class Trade(Base):
    """Executed or planned trade record."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_ticker = Column(String(64), nullable=False, index=True)
    side = Column(String(16), nullable=False)
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    expected_profit = Column(Float, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(32), nullable=True)


class Position(Base):
    """Open or closed position in a market."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_ticker = Column(String(64), nullable=False, index=True)
    side = Column(String(16), nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    size = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    status = Column(String(32), nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow)


class Opportunity(Base):
    """Detected opportunity: logic, arb, combo, or value."""

    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_ticker = Column(String(64), nullable=False, index=True)
    type = Column(String(32), nullable=False)  # logic, arb, combo, value
    edge = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
