import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv('DATABASE_URL')

# Trading
PAPER_MODE = True  # Always paper trade for now
BANKROLL = 1000.0
MIN_ARB_PROFIT = 0.02  # 2% minimum profit

# Bot behavior
SCAN_INTERVAL = 10  # seconds
