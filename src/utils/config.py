"""Load and expose configuration from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


def load_config() -> None:
    """Load environment variables from .env. Called implicitly via dotenv at import."""
    load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes")


POLYMARKET_API_KEY = os.environ.get("POLYMARKET_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
BANKROLL = float(os.environ.get("BANKROLL", "1000"))
PAPER_MODE = _bool_env("PAPER_MODE", True)
