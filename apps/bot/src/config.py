import os
from dotenv import load_dotenv

load_dotenv(".env.local")

# Database (Convex replaces Neon)
CONVEX_URL = os.getenv("CONVEX_URL")
DATABASE_URL = os.getenv("DATABASE_URL")  # legacy, unused when CONVEX_URL set

# Trading
PAPER_MODE = True
BANKROLL = 1000.0
DEFAULT_POSITION_SIZE = 1.0  # $1 per trade (simulate real-money scale)

# CLOB (Polymarket) - required when PAPER_MODE=False
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # EOA private key (hex, with or without 0x)
POLYMARKET_CLOB_HOST = os.getenv("POLYMARKET_CLOB_HOST", "https://clob.polymarket.com")
POLYMARKET_CHAIN_ID = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))
POLYMARKET_SIGNATURE_TYPE = int(os.getenv("POLYMARKET_SIGNATURE_TYPE", "2"))  # 0=EOA, 2=proxy
POLYMARKET_FUNDER_ADDRESS = os.getenv("POLYMARKET_FUNDER_ADDRESS")  # Required if signature_type=2
# Optional: skip create_or_derive_api_key if set
POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY")
POLYMARKET_API_SECRET = os.getenv("POLYMARKET_API_SECRET")
POLYMARKET_API_PASSPHRASE = os.getenv("POLYMARKET_API_PASSPHRASE")

# Bot behavior
SCAN_INTERVAL = 10  # seconds

# STRATEGY CONFIGURATION
STRATEGIES = {
  "last_second": {
    "enabled": True,
    "trigger_seconds": 30,
    "position_size": DEFAULT_POSITION_SIZE,  # $1 per trade
    "min_move_pct": 0.05,  # Minimum move % before betting (0 = disabled)
    "min_move_dollars": 0,  # Minimum move $ before betting (0 = disabled)
    "require_resolution_source_match": False,  # If True, skip when Polymarket uses different feed (e.g. Chainlink)
  },
}

STRATEGY_PRIORITY = ["last_second"]
