"""Execution module for 15-min signal engine. Builds signal and calls executor."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

from src.executor import execute_trade


def execute_signal_engine_trade(
  market: Dict[str, Any],
  signal: Dict[str, Any],
  signal_type: str,
  confidence_layers: int,
  market_end_time: Optional[datetime] = None,
) -> bool:
  """
  Execute a paper trade from the signal engine.
  Adds signal_type, confidence_layers, market_end_time to the trade payload.
  """
  signal = dict(signal)
  signal["strategy"] = "signal_engine"
  signal["signal_type"] = signal_type
  signal["confidence_layers"] = confidence_layers
  if market_end_time is not None:
    signal["market_end_time"] = market_end_time
  return execute_trade(market, signal)
