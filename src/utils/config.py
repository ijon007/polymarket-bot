"""Load and expose environment variables and trading thresholds."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
POLYMARKET_PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY", "")

# Trading config
PAPER_MODE = os.getenv("PAPER_MODE", "True").lower() in ("true", "1", "yes")
BANKROLL = float(os.getenv("BANKROLL", "1000"))

# Thresholds
MIN_LIQUIDITY = int(os.getenv("MIN_LIQUIDITY", "1000"))
MIN_EDGE_LOGIC = float(os.getenv("MIN_EDGE_LOGIC", "0.10"))
MIN_EDGE_ARB = float(os.getenv("MIN_EDGE_ARB", "0.03"))
MIN_EDGE_ARB_QUICK = float(os.getenv("MIN_EDGE_ARB_QUICK", "0.02"))  # 2% for <1hr markets
MIN_EDGE_ARB_NORMAL = float(os.getenv("MIN_EDGE_ARB_NORMAL", "0.03"))  # 3% for regular
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.05"))
MAX_POSITION_SIZE_LOGIC = float(os.getenv("MAX_POSITION_SIZE_LOGIC", "0.10"))
MAX_POSITION_SIZE_ARB = float(os.getenv("MAX_POSITION_SIZE_ARB", "0.15"))
MAX_TOTAL_EXPOSURE = float(os.getenv("MAX_TOTAL_EXPOSURE", "0.40"))
MAX_CATEGORY_EXPOSURE = float(os.getenv("MAX_CATEGORY_EXPOSURE", "0.15"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "10"))

# Bot behavior
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "5"))
QUICK_MARKET_MAX_SECONDS = int(os.getenv("QUICK_MARKET_MAX_SECONDS", "3600"))  # ending soon
FAST_SCAN_INTERVAL = int(os.getenv("FAST_SCAN_INTERVAL", "10"))  # fast loop interval (seconds)
STOP_LOSS = float(os.getenv("STOP_LOSS", "-0.25"))
TAKE_PROFIT = float(os.getenv("TAKE_PROFIT", "0.50"))
