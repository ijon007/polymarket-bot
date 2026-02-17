"""
RTDS WebSocket client for 15-min signal engine.
Uses RTDS_WS_URL from config. Subscribes to BTC price stream.
Exposes get_latest_btc_usd() and get_btc_move_60s() for last-second gate.
"""
import json
import threading
import time
from typing import Any, List, Optional, Tuple

from loguru import logger

try:
  import websocket
except ImportError:
  websocket = None

from src.config import RTDS_WS_URL

_PING_INTERVAL = 6
_PING_TIMEOUT = 3
_RECONNECT_DELAY = 5
_MAX_RECONNECT_DELAY = 60
_RATE_LIMIT_BACKOFF_SEC = 60
_BUFFER_MS = 10 * 60 * 1000  # 10 minutes

_lock = threading.Lock()
_rate_limited = False
_latest_btc_usd: Optional[float] = None
_latest_ts_ms: Optional[int] = None
_buffer: List[Tuple[int, float]] = []
_ws: Optional["websocket.WebSocketApp"] = None
_thread: Optional[threading.Thread] = None
_stop = threading.Event()


def _evict_old(now_ms: int) -> None:
  global _buffer
  cutoff = now_ms - _BUFFER_MS
  _buffer[:] = [(t, v) for t, v in _buffer if t >= cutoff]


def _on_message(_: Any, message: str) -> None:
  global _latest_btc_usd, _latest_ts_ms, _buffer
  if not message or not message.strip():
    return
  try:
    data = json.loads(message)
    topic = data.get("topic")
    payload = data.get("payload") or {}
    if topic == "crypto_prices_chainlink" and payload.get("symbol") == "btc/usd":
      value = payload.get("value")
      ts = payload.get("timestamp")
      if value is not None:
        v = float(value)
        ts_ms = int(ts) if ts is not None else None
        with _lock:
          _latest_btc_usd = v
          _latest_ts_ms = ts_ms
          if ts_ms is not None:
            _buffer.append((ts_ms, v))
            _buffer.sort(key=lambda x: x[0])
            _evict_old(ts_ms)
  except Exception as e:
    logger.debug(f"RTDS parse error: {e}")


def _on_error(_: Any, error: Exception) -> None:
  global _rate_limited
  err_str = str(error).lower()
  if "429" in err_str or "too many requests" in err_str:
    _rate_limited = True
    logger.warning("RTDS rate limited (429); backing off before reconnect")
  elif "getaddrinfo failed" in err_str or "11001" in err_str:
    logger.warning("RTDS WebSocket DNS/network error")
  else:
    logger.warning(f"RTDS WebSocket error: {error}")


def _on_close(_: Any, close_status_code: int, close_msg: str) -> None:
  logger.info(f"RTDS WebSocket closed: {close_status_code} {close_msg}")


def _on_open(ws: Any) -> None:
  sub = {
    "action": "subscribe",
    "subscriptions": [
      {
        "topic": "crypto_prices_chainlink",
        "type": "*",
        "filters": '{"symbol":"btc/usd"}',
      }
    ],
  }
  ws.send(json.dumps(sub))
  logger.info("RTDS (15min) subscribed to crypto_prices_chainlink (btc/usd)")


def _run_loop() -> None:
  global _ws, _rate_limited
  delay = _RECONNECT_DELAY
  while not _stop.is_set():
    try:
      if websocket is None:
        logger.error("websocket-client not installed; RTDS disabled")
        break
      _ws = websocket.WebSocketApp(
        RTDS_WS_URL,
        on_message=_on_message,
        on_error=_on_error,
        on_close=_on_close,
        on_open=_on_open,
      )
      _ws.run_forever(ping_interval=_PING_INTERVAL, ping_timeout=_PING_TIMEOUT)
    except Exception as e:
      logger.warning(f"RTDS connection failed: {e}")
    if _stop.is_set():
      break
    if _rate_limited:
      delay = max(delay, _RATE_LIMIT_BACKOFF_SEC)
      _rate_limited = False
    time.sleep(delay)
    delay = min(delay * 1.5, _MAX_RECONNECT_DELAY)
  _ws = None


def start() -> None:
  """Start RTDS WebSocket in a daemon thread."""
  global _thread
  if _thread is not None and _thread.is_alive():
    return
  _stop.clear()
  _thread = threading.Thread(target=_run_loop, daemon=True)
  _thread.start()
  logger.info("RTDS (15min) client started")


def stop() -> None:
  """Stop the RTDS WebSocket."""
  global _ws
  _stop.set()
  if _ws:
    try:
      _ws.close()
    except Exception:
      pass
    _ws = None


def get_latest_btc_usd() -> Optional[float]:
  """Return latest BTC/USD (thread-safe)."""
  with _lock:
    return _latest_btc_usd


def get_btc_move_60s() -> Optional[float]:
  """
  Return BTC price change (as decimal, e.g. 0.003 = 0.3%) over last 60 seconds.
  Returns None if insufficient data.
  """
  now_ms = int(time.time() * 1000)
  cutoff_ms = now_ms - 60 * 1000
  with _lock:
    if not _buffer or _latest_btc_usd is None:
      return None
    price_at_cutoff = None
    for t, v in _buffer:
      if t <= cutoff_ms:
        price_at_cutoff = v
      else:
        break
    if price_at_cutoff is None or price_at_cutoff <= 0:
      return None
    return (_latest_btc_usd - price_at_cutoff) / price_at_cutoff


def get_btc_at_timestamp(ts_unix_seconds: int) -> Optional[float]:
  """Return BTC price at given Unix timestamp (seconds)."""
  if ts_unix_seconds <= 0:
    return None
  ts_ms = ts_unix_seconds * 1000
  with _lock:
    if not _buffer:
      return None
    last_at_or_before = None
    for t, v in _buffer:
      if t > ts_ms:
        break
      last_at_or_before = v
    return last_at_or_before
