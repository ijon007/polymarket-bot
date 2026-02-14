from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger
from src.config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
Session = sessionmaker(bind=engine) if engine else None


class Trade(Base):
  __tablename__ = "trades"

  id = Column(Integer, primary_key=True, autoincrement=True)
  condition_id = Column(String)
  question = Column(String)
  yes_price = Column(Float)
  no_price = Column(Float)
  total_cost = Column(Float)
  position_size = Column(Float)
  expected_profit = Column(Float)
  profit_pct = Column(Float)
  executed_at = Column(DateTime)
  status = Column(String)


def init_db():
  """Create tables if they don't exist"""
  if not engine:
    logger.warning("DATABASE_URL not set - skipping database init")
    return
  Base.metadata.create_all(engine)
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
