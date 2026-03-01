from src.strategies.base import BaseStrategy
from src.utils.price_feed import get_btc_price_history
from typing import Optional, Dict, List, Tuple
from loguru import logger


def _resample_to_1min(history: List[Tuple[int, float]]) -> List[float]:
  """
  Resample (ts_ms, price) ticks to 1-minute series.
  For each minute, use last price in that minute. Returns [p1, p2, ...] oldest first.
  """
  if not history:
    return []
  by_minute: Dict[int, float] = {}
  for ts_ms, price in history:
    minute_ts = ts_ms // 60000
    by_minute[minute_ts] = price
  sorted_minutes = sorted(by_minute.keys())
  return [by_minute[m] for m in sorted_minutes]


class TechnicalAnalysisStrategy(BaseStrategy):
  """
  Predict BTC direction using technical indicators.

  Uses 3 indicators:
  1. EMA(5) vs EMA(15) - Trend direction
  2. RSI(14) - Overbought/oversold
  3. Rate of Change - Momentum acceleration

  Requires 2/3 consensus to trade.
  """

  def __init__(self, config: Dict):
    super().__init__("Technical Analysis", config)

    self.ema_short = config.get("ema_short", 5)
    self.ema_long = config.get("ema_long", 15)
    self.rsi_period = config.get("rsi_period", 14)
    self.rsi_oversold = config.get("rsi_oversold", 30)
    self.rsi_overbought = config.get("rsi_overbought", 70)
    self.roc_period = config.get("roc_period", 10)
    self.roc_threshold = config.get("roc_threshold", 0.5)
    self.min_data_points = config.get("min_data_points", 20)
    self.trade_window_start = config.get("trade_window_start", 900)
    self.trade_window_end = config.get("trade_window_end", 120)

  def should_trade(self, market: Dict) -> bool:
    if not self.enabled:
      return False
    if (market.get("asset") or "").strip().lower() != "btc":
      return False
    seconds_left = market.get("seconds_left", 0)
    return self.trade_window_end < seconds_left <= self.trade_window_start

  def get_price_history(self) -> List[Tuple[int, float]]:
    return get_btc_price_history()

  def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
      return None
    recent_prices = prices[-period:]
    multiplier = 2 / (period + 1)
    ema = recent_prices[0]
    for price in recent_prices[1:]:
      ema = (price * multiplier) + (ema * (1 - multiplier))
    return ema

  def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
      return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent_deltas = deltas[-period:]
    gains = [d if d > 0 else 0 for d in recent_deltas]
    losses = [-d if d < 0 else 0 for d in recent_deltas]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
      return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

  def calculate_roc(self, prices: List[float], period_minutes: int = 10) -> Optional[float]:
    if len(prices) < period_minutes:
      return None
    current_price = prices[-1]
    past_price = prices[-period_minutes]
    return ((current_price - past_price) / past_price) * 100

  def generate_signals(self, prices: List[float]) -> Optional[Dict]:
    ema_short = self.calculate_ema(prices, self.ema_short)
    ema_long = self.calculate_ema(prices, self.ema_long)
    rsi = self.calculate_rsi(prices, self.rsi_period)
    roc = self.calculate_roc(prices, self.roc_period)

    if None in (ema_short, ema_long, rsi, roc):
      return None

    signals = []
    details = {}

    if ema_short > ema_long:
      signals.append("UP")
      ema_signal = "UP"
    else:
      signals.append("DOWN")
      ema_signal = "DOWN"
    details["ema"] = {"short": ema_short, "long": ema_long, "signal": ema_signal}

    if rsi < self.rsi_oversold:
      signals.append("UP")
      rsi_signal = "UP (oversold)"
    elif rsi > self.rsi_overbought:
      signals.append("DOWN")
      rsi_signal = "DOWN (overbought)"
    else:
      signals.append("NEUTRAL")
      rsi_signal = "NEUTRAL"
    details["rsi"] = {"value": rsi, "signal": rsi_signal}

    if roc > self.roc_threshold:
      signals.append("UP")
      roc_signal = "UP"
    elif roc < -self.roc_threshold:
      signals.append("DOWN")
      roc_signal = "DOWN"
    else:
      signals.append("NEUTRAL")
      roc_signal = "NEUTRAL"
    details["roc"] = {"value": roc, "signal": roc_signal}

    return {"signals": signals, "details": details}

  def analyze(self, market: Dict) -> Optional[Dict]:
    if not self.should_trade(market):
      return None

    price_history = self.get_price_history()
    prices = _resample_to_1min(price_history)

    if len(prices) < self.min_data_points:
      logger.debug(
        f"Insufficient price history: {len(prices)} points (need {self.min_data_points})"
      )
      return None

    signal_result = self.generate_signals(prices)
    if not signal_result:
      return None

    signals = signal_result["signals"]
    details = signal_result["details"]

    up_votes = signals.count("UP")
    down_votes = signals.count("DOWN")

    if up_votes >= 2:
      action = "bet_yes"
      price = market["yes_price"]
      direction = "UP"
      confidence = 0.65 if up_votes == 2 else 0.80
    elif down_votes >= 2:
      action = "bet_no"
      price = market["no_price"]
      direction = "DOWN"
      confidence = 0.65 if down_votes == 2 else 0.80
    else:
      logger.debug(
        f"No consensus: UP={up_votes}, DOWN={down_votes} | "
        f"EMA: {details['ema']['signal']}, "
        f"RSI: {details['rsi']['signal']}, "
        f"ROC: {details['roc']['signal']}"
      )
      return None

    reason = (
      f"Technical {direction}: "
      f"EMA({self.ema_short}/{self.ema_long})={details['ema']['signal']}, "
      f"RSI({details['rsi']['value']:.0f})={details['rsi']['signal']}, "
      f"ROC({details['roc']['value']:+.2f}%)={details['roc']['signal']}"
    )

    logger.info(
      f"[TECHNICAL] {market['slug']} | "
      f"{reason} → {action.upper()} "
      f"({up_votes if direction == 'UP' else down_votes}/3 votes)"
    )

    edge = abs(price - 0.50)
    expected_profit = edge * self.config.get("position_size", 100)

    return {
      "strategy": self.name,
      "action": action,
      "price": price,
      "size": self.config.get("position_size", 100),
      "confidence": confidence,
      "reason": reason,
      "expected_profit": expected_profit,
    }
