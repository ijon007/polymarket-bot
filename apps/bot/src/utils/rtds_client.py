"""
Polymarket RTDS WebSocket client for Chainlink BTC price.
Subscribes to crypto_prices_chainlink (btc/usd) - same feed Polymarket uses for resolution.
Keeps a rolling buffer of (timestamp_ms, value) for start-price lookups.
"""
import json
import threading
import time
from typing import List, Optional, Tuple

from loguru import logger

try:
  import websocket
except ImportError:
  websocket = None

_WS_URL = "wss://ws-live-data.polymarket.com"
_PING_INTERVAL = 6
_PING_TIMEOUT = 3
_RECONNECT_DELAY = 5
_MAX_RECONNECT_DELAY = 60
_BUFFER_MS = 10 * 60 * 1000  # 10 minutes

_lock = threading.Lock()
_latest_btc_usd: Optional[float] = None
_latest_ts_ms: Optional[int] = None
_buffer: List[Tuple[int, float]] = []  # (ts_ms, value), ascending ts_ms
_ws: Optional["websocket.WebSocketApp"] = None
_thread: Optional[threading.Thread] = None
_stop = threading.Event()


def _evict_old(now_ms: int) -> None:
  global _buffer
  cutoff = now_ms - _BUFFER_MS
  _buffer = [(t, v) for t, v in _buffer if t >= cutoff]


def _on_message(_, message: str) -> None:
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
      logger.debug(f"BTC price (RTDS): ${float(value):,.2f}")
  except Exception as e:
    logger.debug(f"RTDS parse error: {e}")


def _on_error(_, error: Exception) -> None:
  err_str = str(error).lower()
  if "getaddrinfo failed" in err_str or "11001" in err_str or "name or service not known" in err_str:
    logger.warning(
      f"RTDS WebSocket DNS/network error: cannot resolve {_WS_URL} — "
      "check internet, DNS, VPN/firewall, or try another network"
    )
  else:
    logger.warning(f"RTDS WebSocket error: {error}")


def _on_close(_, close_status_code, close_msg) -> None:
  logger.info(f"RTDS WebSocket closed: {close_status_code} {close_msg}")


def _on_open(ws: "websocket.WebSocketApp") -> None:
  sub = {
    "action": "subscribe",
    "subscriptions": [
      {
        "topic": "crypto_prices_chainlink",
        "type": "*",
        "filters": '{"symbol":"btc/usd"}'
      }
    ]
  }
  ws.send(json.dumps(sub))
  logger.info("RTDS subscribed to crypto_prices_chainlink (btc/usd)")


def _run_loop() -> None:
  global _ws
  delay = _RECONNECT_DELAY
  last_ping = 0.0
  while not _stop.is_set():
    try:
      if websocket is None:
        logger.error(
          "websocket-client not installed; RTDS disabled. "
          "From your venv run: pip install websocket-client"
        )
        break
      _ws = websocket.WebSocketApp(
        _WS_URL,
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
  logger.info("RTDS client started")


def stop() -> None:
  """Signal RTDS thread to stop and close connection."""
  global _ws
  _stop.set()
  if _ws:
    try:
      _ws.close()
    except Exception:
      pass
    _ws = None


def get_latest_btc_usd() -> Optional[float]:
  """Return latest BTC/USD from RTDS chainlink stream (thread-safe)."""
  with _lock:
    return _latest_btc_usd


def get_btc_at_timestamp(ts_unix_seconds: int) -> Optional[float]:
  """
  Return BTC price at the given Unix timestamp (seconds): last tick with timestamp <= T.
  Matches oracle semantics (price that was current at that moment). Returns None if we
  have no tick at or before T (e.g. we connected after that time).
  """
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
