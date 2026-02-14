import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv('DATABASE_URL')

# Trading
PAPER_MODE = True
BANKROLL = 1000.0
DEFAULT_POSITION_SIZE = 10.0  # $10 per trade (simulate real-money scale)

# Bot behavior
SCAN_INTERVAL = 10  # seconds

# Price feed: use Polymarket RTDS (Chainlink) for current BTC when available
USE_RTDS = os.getenv("USE_RTDS", "true").lower() in ("true", "1", "yes")

# STRATEGY CONFIGURATION
# Toggle strategies on/off and configure parameters
STRATEGIES = {
  "mean_reversion": {
    "enabled": False,
    "overpriced_threshold": 0.60,  # Consider overpriced above 60¢
    "min_edge": 0.08,  # 8% minimum edge
    "position_size": DEFAULT_POSITION_SIZE
  },
  "momentum": {
    "enabled": False,
    "lookback_seconds": 60,
    "min_move_pct": 0.002,  # 0.2% minimum move
    "position_size": DEFAULT_POSITION_SIZE
  },
  "last_second": {
    "enabled": True,
    "trigger_seconds": 30,
    "position_size": DEFAULT_POSITION_SIZE,  # $10 per trade
    "min_move_pct": 0.05,  # Minimum move % before betting (0 = disabled)
    "min_move_dollars": 0,  # Minimum move $ before betting (0 = disabled)
    "require_resolution_source_match": False,  # If True, skip when Polymarket uses different feed (e.g. Chainlink)
  },
  "spread_capture": {
    "enabled": False,  # Disabled (requires limit order infrastructure)
    "spread_target": 0.02,
    "position_size": DEFAULT_POSITION_SIZE
  }
}

# Priority order (if multiple strategies trigger, use highest priority)
STRATEGY_PRIORITY = [
  "last_second",
  "momentum",
  "mean_reversion",
  "spread_capture"
]
