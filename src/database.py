import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger
from src.config import DATABASE_URL

Base = declarative_base()
engine = None
if DATABASE_URL:
  try:
    engine = create_engine(DATABASE_URL)
  except ModuleNotFoundError as e:
    if "psycopg2" in str(e):
      raise ModuleNotFoundError(
        "PostgreSQL driver not installed. From your project venv run: pip install psycopg2-binary"
      ) from e
    raise
Session = sessionmaker(bind=engine) if engine else None


def _migrate_schema_on_engine(eng):
  """Add missing columns to existing trades table (schema migration) on the given engine."""
  try:
    with eng.connect() as conn:
      conn.execute(text("""
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS market_ticker VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS condition_id VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS question VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS strategy VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS action VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS side VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS price FLOAT;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS yes_price FLOAT;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS no_price FLOAT;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS position_size FLOAT;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS size FLOAT;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS expected_profit FLOAT;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS confidence FLOAT;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS reason VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS executed_at TIMESTAMP;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS status VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS market_outcome VARCHAR;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS actual_profit FLOAT;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP;
      """))
      conn.commit()
      # Convert timestamp columns to TIMESTAMPTZ so UTC is stored unambiguously
      for stmt in (
        "ALTER TABLE trades ALTER COLUMN executed_at TYPE TIMESTAMPTZ USING executed_at AT TIME ZONE 'UTC'",
        "ALTER TABLE trades ALTER COLUMN settled_at TYPE TIMESTAMPTZ USING settled_at AT TIME ZONE 'UTC'",
        "ALTER TABLE market_outcomes ALTER COLUMN resolved_at TYPE TIMESTAMPTZ USING resolved_at AT TIME ZONE 'UTC'",
      ):
        try:
          conn.execute(text(stmt))
          conn.commit()
        except Exception:
          pass  # Column may already be TIMESTAMPTZ
    logger.info("Schema migration completed")
  except Exception as e:
    logger.warning(f"Schema migration: {e}")


def _migrate_schema():
  """Add missing columns to existing trades table (schema migration)."""
  if not engine:
    return
  _migrate_schema_on_engine(engine)


class Trade(Base):
  __tablename__ = "trades"

  id = Column(Integer, primary_key=True, autoincrement=True)
  market_ticker = Column(String, nullable=False)  # e.g. btc-updown-5m-1771083600
  condition_id = Column(String)
  question = Column(String)
  strategy = Column(String)  # which strategy triggered
  action = Column(String)  # YES, NO, or ARBITRAGE
  side = Column(String, nullable=False)  # YES, NO, or ARBITRAGE (DB requires this)
  price = Column(Float, nullable=True)  # For directional bets
  yes_price = Column(Float, nullable=True)  # For arbitrage
  no_price = Column(Float, nullable=True)  # For arbitrage
  position_size = Column(Float)
  size = Column(Float, nullable=False)  # DB column (same as position_size)
  expected_profit = Column(Float)
  confidence = Column(Float)
  reason = Column(String)
  executed_at = Column(DateTime(timezone=True))  # UTC
  status = Column(String)
  market_outcome = Column(String, nullable=True)  # YES or NO when settled
  actual_profit = Column(Float, nullable=True)  # Realized P&L
  settled_at = Column(DateTime(timezone=True), nullable=True)  # UTC


class MarketOutcome(Base):
  __tablename__ = "market_outcomes"

  id = Column(Integer, primary_key=True, autoincrement=True)
  slug = Column(String, unique=True)
  condition_id = Column(String)
  outcome = Column(String)  # YES or NO
  resolved_at = Column(DateTime(timezone=True))  # UTC
  btc_start_price = Column(Float, nullable=True)
  btc_end_price = Column(Float, nullable=True)


def init_db():
  """Create tables if they don't exist"""
  if not engine:
    logger.warning("DATABASE_URL not set - skipping database init")
    return
  try:
    Base.metadata.create_all(engine)
    _migrate_schema()
    logger.info("Database initialized")
  except OperationalError as e:
    logger.error(
      "Database connection failed (check network/DNS and DATABASE_URL). "
      "To run without a database, unset DATABASE_URL in .env."
    )
    logger.error(str(e.orig) if getattr(e, "orig", None) else str(e))
    sys.exit(1)


def init_db_at_url(database_url: str):
  """
  Scaffold the database at the given URL: create all tables and run migrations.
  Use this to initialize a different DB than DATABASE_URL (e.g. for a separate env or local copy).
  """
  url = (database_url or "").strip()
  if not url:
    raise ValueError("database_url is required and must be non-empty")
  try:
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    _migrate_schema_on_engine(eng)
    logger.info("Database initialized at given URL")
  except ModuleNotFoundError as e:
    if "psycopg2" in str(e):
      raise ModuleNotFoundError(
        "PostgreSQL driver not installed. From your project venv run: pip install psycopg2-binary"
      ) from e
    raise
  except OperationalError as e:
    logger.error("Database connection failed (check URL, network, and credentials).")
    raise


def _dummy_trade_payload():
  """Same shape as executor sends (directional bet). Used for dry-run insert."""
  return {
    "market_ticker": "test-dry-run",
    "condition_id": "0x00",
    "question": "test",
    "strategy": "test",
    "action": "YES",
    "side": "YES",
    "price": 0.5,
    "yes_price": 0.5,
    "no_price": 0.5,
    "position_size": 0.0,
    "size": 0.0,
    "expected_profit": 0.0,
    "confidence": 0.0,
    "reason": "DB schema check",
    "executed_at": datetime.now(timezone.utc),
    "status": "paper",
  }


def validate_db_schema():
  """
  Run before trading: do a dry-run INSERT then ROLLBACK.
  Raises if the trades table has NOT NULL columns we don't fill.
  Call this after init_db() and exit if it fails.
  """
  if not Session:
    return
  session = None
  try:
    safe = _sanitize_trade_data(_dummy_trade_payload())
    allowed = {c.key for c in Trade.__table__.columns if c.key != "id"}
    payload = {k: safe[k] for k in allowed if k in safe}
    session = Session()
    trade = Trade(**payload)
    session.add(trade)
    session.flush()
    session.rollback()
    logger.info("DB schema check passed: trades table is compatible")
  except Exception as e:
    if session:
      try:
        session.rollback()
      except Exception:
        pass
      try:
        session.close()
      except Exception:
        pass
    raise RuntimeError(
      f"Database schema check FAILED. Fix before trading.\n"
      f"Error: {e}\n"
      f"Your 'trades' table may have NOT NULL columns missing from the app. "
      f"Run: python scripts/check_db.py"
    ) from e
  finally:
    if session:
      try:
        session.close()
      except Exception:
        pass


# Columns that must not be None for INSERT (match typical NOT NULL constraints)
_REQUIRED_KEYS = (
  "market_ticker", "condition_id", "question", "strategy", "action", "side",
  "position_size", "size", "expected_profit", "confidence", "reason", "executed_at", "status"
)


def _sanitize_trade_data(data):
  """Ensure all required fields have non-null values to avoid NOT NULL violations."""
  out = dict(data)
  if not (out.get("market_ticker") or "").strip():
    out["market_ticker"] = out.get("question") or out.get("condition_id") or "unknown"
  for key in _REQUIRED_KEYS:
    if key in out and out[key] is None:
      if key in ("condition_id", "question", "strategy", "action", "side", "reason", "status"):
        out[key] = ""
      elif key in ("position_size", "size", "expected_profit", "confidence"):
        out[key] = 0.0
      elif key == "executed_at":
        out[key] = datetime.now(timezone.utc)
  return out


def has_open_trade_for_market(slug: str) -> bool:
  """True if we already have an unsettled (paper) trade on this market."""
  if not Session or not slug:
    return False
  session = None
  try:
    session = Session()
    return session.query(Trade).filter(
      Trade.market_ticker == slug,
      Trade.status == "paper"
    ).limit(1).first() is not None
  except Exception:
    return False
  finally:
    if session:
      try:
        session.close()
      except Exception:
        pass


def log_trade(trade_data):
  """Save trade to database. Never raises - logging is best-effort so execution is never blocked."""
  if not Session:
    logger.warning("Database not configured - trade not logged")
    return
  session = None
  try:
    safe = _sanitize_trade_data(trade_data)
    # Only pass keys that exist on Trade model
    allowed = {c.key for c in Trade.__table__.columns if c.key != "id"}
    payload = {k: safe[k] for k in allowed if k in safe}
    session = Session()
    trade = Trade(**payload)
    session.add(trade)
    session.commit()
  except Exception as e:
    logger.error(f"Error logging trade: {e}")
  finally:
    if session:
      try:
        session.close()
      except Exception:
        pass
