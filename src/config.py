import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv('DATABASE_URL')

# Trading
PAPER_MODE = True
BANKROLL = 1000.0
DEFAULT_POSITION_SIZE = 100.0  # $100 per trade

# Bot behavior
SCAN_INTERVAL = 10  # seconds

# STRATEGY CONFIGURATION
# Toggle strategies on/off and configure parameters
STRATEGIES = {
  "mean_reversion": {
    "enabled": True,
    "overpriced_threshold": 0.60,  # Consider overpriced above 60¢
    "min_edge": 0.08,  # 8% minimum edge
    "position_size": DEFAULT_POSITION_SIZE
  },
  "momentum": {
    "enabled": False,  # Disabled until Chainlink integration
    "lookback_seconds": 60,
    "min_move_pct": 0.001,  # 0.1% move
    "position_size": DEFAULT_POSITION_SIZE
  },
  "last_second": {
    "enabled": False,  # Disabled until Chainlink integration
    "trigger_seconds": 30,
    "position_size": DEFAULT_POSITION_SIZE * 2  # Higher size for near-certain bets
  },
  "spread_capture": {
    "enabled": False,  # Disabled (requires limit order infrastructure)
    "spread_target": 0.02,
    "position_size": DEFAULT_POSITION_SIZE
  }
}

# Priority order (if multiple strategies trigger, use highest priority)
STRATEGY_PRIORITY = [
  "last_second",    # High (near-certain)
  "mean_reversion", # Medium
  "momentum",       # Medium
  "spread_capture"  # Lowest
]
