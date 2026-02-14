"""Load and expose environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
POLYMARKET_PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY", "")
BANKROLL = float(os.getenv("BANKROLL", "1000"))
PAPER_MODE = os.getenv("PAPER_MODE", "True").lower() in ("true", "1", "yes")
