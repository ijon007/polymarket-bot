#!/usr/bin/env python3
"""
Run this BEFORE starting the bot to confirm the database schema is compatible.
Exits 0 if OK, 1 if the trades table will cause NOT NULL or other insert errors.
"""
import sys
import os

# Run from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from src.database import init_db, validate_db_schema

def main():
  logger.info("Checking database schema...")
  init_db()
  try:
    validate_db_schema()
    logger.success("DB check passed. Safe to run the bot.")
    return 0
  except RuntimeError as e:
    logger.error(str(e))
    return 1
  except Exception as e:
    logger.error(f"DB check failed: {e}")
    return 1

if __name__ == "__main__":
  sys.exit(main())
