"""Minimal tests for config."""

import sys
import os

# Ensure src is on path when running tests from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_config_import_and_defaults():
    """Config loads and exposes expected types (PAPER_MODE bool, BANKROLL float)."""
    from src.utils import config
    assert isinstance(config.PAPER_MODE, bool)
    assert isinstance(config.BANKROLL, (int, float))
    assert config.BANKROLL >= 0
