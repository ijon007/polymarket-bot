#!/usr/bin/env python3
"""
Convex: schema is deployed via npx convex dev. No init needed.
Legacy: previously scaffolded Postgres via DATABASE_URL.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from src.config import CONVEX_URL


def main():
  if CONVEX_URL:
    logger.info("Convex schema is deployed via npx convex dev. No init needed.")
    logger.success("Database (Convex) ready.")
    return 0
  logger.error("CONVEX_URL not set. Set CONVEX_URL in .env.local (created by npx convex dev).")
  return 1


if __name__ == "__main__":
  sys.exit(main())
