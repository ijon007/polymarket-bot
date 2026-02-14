from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger
from src.config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
Session = sessionmaker(bind=engine) if engine else None


def _migrate_schema():
    """Add missing columns to existing trades table (schema migration)."""
    if not engine:
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS condition_id VARCHAR;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS question VARCHAR;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS strategy VARCHAR;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS action VARCHAR;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS price FLOAT;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS yes_price FLOAT;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS no_price FLOAT;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS position_size FLOAT;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS expected_profit FLOAT;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS confidence FLOAT;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS reason VARCHAR;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS executed_at TIMESTAMP;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS status VARCHAR;
            """))
            conn.commit()
        logger.info("Schema migration completed")
    except Exception as e:
        logger.warning(f"Schema migration: {e}")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    condition_id = Column(String)
    question = Column(String)
    strategy = Column(String)  # which strategy triggered
    action = Column(String)  # YES, NO, or ARBITRAGE
    price = Column(Float, nullable=True)  # For directional bets
    yes_price = Column(Float, nullable=True)  # For arbitrage
    no_price = Column(Float, nullable=True)  # For arbitrage
    position_size = Column(Float)
    expected_profit = Column(Float)
    confidence = Column(Float)
    reason = Column(String)
    executed_at = Column(DateTime)
    status = Column(String)


def init_db():
    """Create tables if they don't exist"""
    if not engine:
        logger.warning("DATABASE_URL not set - skipping database init")
        return
    Base.metadata.create_all(engine)
    _migrate_schema()
    logger.info("Database initialized")


def log_trade(trade_data):
    """Save trade to database"""
    if not Session:
        logger.warning("Database not configured - trade not logged")
        return
    try:
        session = Session()
        trade = Trade(**trade_data)
        session.add(trade)
        session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Error logging trade: {e}")
