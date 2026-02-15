import os
from dotenv import load_dotenv

load_dotenv(".env.local")

# Database (Convex replaces Neon)
CONVEX_URL = os.getenv("CONVEX_URL")
DATABASE_URL = os.getenv("DATABASE_URL")  # legacy, unused when CONVEX_URL set

# Trading
PAPER_MODE = True
BANKROLL = 1000.0
DEFAULT_POSITION_SIZE = 10.0  # $10 per trade (simulate real-money scale)

# Bot behavior
SCAN_INTERVAL = 10  # seconds

# STRATEGY CONFIGURATION
STRATEGIES = {
  "last_second": {
    "enabled": True,
    "trigger_seconds": 30,
    "position_size": DEFAULT_POSITION_SIZE,  # $10 per trade
    "min_move_pct": 0.05,  # Minimum move % before betting (0 = disabled)
    "min_move_dollars": 0,  # Minimum move $ before betting (0 = disabled)
    "require_resolution_source_match": False,  # If True, skip when Polymarket uses different feed (e.g. Chainlink)
  },
}

STRATEGY_PRIORITY = ["last_second"]
