"""Minimal tests for config loading."""

from src.utils import config


def test_config_loads():
    """Config module loads and exposes expected attributes."""
    assert hasattr(config, "GROQ_API_KEY")
    assert hasattr(config, "DATABASE_URL")
    assert hasattr(config, "BANKROLL")
    assert isinstance(config.PAPER_MODE, bool)
