import os
from dotenv import load_dotenv

load_dotenv(".env.local")

# Database (Convex replaces Neon)
CONVEX_URL = os.getenv("CONVEX_URL")

# Trading
PAPER_MODE = True
BANKROLL = 1000.0
DEFAULT_POSITION_SIZE = 10.0  # $1 per trade (simulate real-money scale)

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

# --- 5-min bot: assets to scan/trade (BTC, ETH, SOL, XRP) ---
FIVE_MIN_ASSETS = [
  a.strip().lower()
  for a in (os.getenv("FIVE_MIN_ASSETS") or "btc,eth,sol,xrp").split(",")
  if a.strip()
]
if not FIVE_MIN_ASSETS:
  FIVE_MIN_ASSETS = ["btc", "eth", "sol", "xrp"]

# --- 15-min signal engine (separate process, main_15min.py) ---
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "10.0"))
# Assets to trade: comma-separated (e.g. "btc,eth,sol,xrp"). Default all four.
LATE_ENTRY_15MIN_ASSETS = [
  a.strip().lower()
  for a in (os.getenv("LATE_ENTRY_15MIN_ASSETS") or "btc,eth,sol,xrp").split(",")
  if a.strip()
]
# Late Entry V3: enter last 4 min, buy favorite (higher ask), flat size
LATE_ENTRY_WINDOW_SEC = int(os.getenv("LATE_ENTRY_WINDOW_SEC", "240"))
LATE_ENTRY_MIN_GAP = float(os.getenv("LATE_ENTRY_MIN_GAP", "0.35"))
LATE_ENTRY_MAX_PRICE = float(os.getenv("LATE_ENTRY_MAX_PRICE", "0.85"))
LATE_ENTRY_SIZE = float(os.getenv("LATE_ENTRY_SIZE", "10.0"))
POLYMARKET_WS_URL = os.getenv(
  "POLYMARKET_WS_URL", "wss://ws-subscriptions-clob.polymarket.com/ws/market"
)
RTDS_WS_URL = os.getenv("RTDS_WS_URL", "wss://ws-live-data.polymarket.com")