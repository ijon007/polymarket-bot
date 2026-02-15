#!/usr/bin/env python3
"""
Scaffold the database: create tables and run migrations.
Uses DATABASE_URL from .env by default. Pass a URL as the first argument to
initialize a different database (e.g. another Postgres instance or a local copy).

  python scripts/init_db.py
  python scripts/init_db.py "postgresql://user:pass@host:5432/mydb"
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from src.config import DATABASE_URL
from src.database import init_db_at_url


def main():
  url = None
  if len(sys.argv) > 1:
    url = sys.argv[1].strip()
  if not url:
    url = DATABASE_URL
  if not url:
    logger.error("No database URL. Set DATABASE_URL in .env or pass it as the first argument.")
    return 1
  try:
    init_db_at_url(url)
    logger.success("Database scaffolded successfully.")
    return 0
  except Exception as e:
    logger.error(f"Init failed: {e}")
    return 1


if __name__ == "__main__":
  sys.exit(main())
