"""
Polymarket RTDS WebSocket client for Chainlink crypto prices (BTC, ETH, SOL, XRP).
Subscribes to crypto_prices_chainlink - same feed Polymarket uses for resolution.
Keeps per-symbol rolling buffers for start-price lookups.
"""
import json
import threading
import time
from typing import Dict, List, Optional, Tuple

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
_START_PRICE_CACHE_MAX_AGE_SEC = 30 * 60  # keep cached start prices for 30 min
_RECENT_WINDOW_SEC = 90  # for new window: if no tick at or before ts, use first tick in buffer

_SYMBOLS = ("btc/usd", "eth/usd", "sol/usd", "xrp/usd")

_lock = threading.Lock()
_latest: Dict[str, float] = {}  # symbol -> latest value
_buffers: Dict[str, List[Tuple[int, float]]] = {s: [] for s in _SYMBOLS}
_start_price_caches: Dict[str, Dict[int, float]] = {s: {} for s in _SYMBOLS}
_ws: Optional["websocket.WebSocketApp"] = None
_thread: Optional[threading.Thread] = None
_stop = threading.Event()
_rtds_log_interval = 5.0  # seconds
_last_rtds_log_time = 0.0


def _evict_old(buf: List[Tuple[int, float]], now_ms: int) -> None:
  cutoff = now_ms - _BUFFER_MS
  buf[:] = [(t, v) for t, v in buf if t >= cutoff]


def _on_message(_, message: str) -> None:
  global _latest, _buffers, _last_rtds_log_time
  if not message or not message.strip():
    return
  try:
    data = json.loads(message)
    topic = data.get("topic")
    payload = data.get("payload") or {}
    if topic != "crypto_prices_chainlink":
      return
    symbol = (payload.get("symbol") or "").strip().lower()
    if symbol not in _SYMBOLS:
      return
    value = payload.get("value")
    ts = payload.get("timestamp")
    if value is not None:
      v = float(value)
      ts_ms = None
      if ts is not None:
        t = int(ts)
        ts_ms = t * 1000 if t < 1_000_000_000_000 else t
      with _lock:
        _latest[symbol] = v
        if ts_ms is not None:
          buf = _buffers[symbol]
          buf.append((ts_ms, v))
          buf.sort(key=lambda x: x[0])
          _evict_old(buf, ts_ms)
      now_sec = time.time()
      if now_sec - _last_rtds_log_time >= _rtds_log_interval:
        with _lock:
          parts = [f"{s.upper().replace('/USD','')}: ${_latest.get(s, 0):,.2f}" for s in _SYMBOLS]
        logger.debug("RTDS: %s", " | ".join(parts))
        _last_rtds_log_time = now_sec
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
      {"topic": "crypto_prices_chainlink", "type": "*", "filters": f'{{"symbol":"{s}"}}'}
      for s in _SYMBOLS
    ]
  }
  ws.send(json.dumps(sub))
  logger.info(f"RTDS subscribed to crypto_prices_chainlink: {', '.join(_SYMBOLS)}")


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
    return _latest.get("btc/usd")


def get_latest_eth_usd() -> Optional[float]:
  with _lock:
    return _latest.get("eth/usd")


def get_latest_sol_usd() -> Optional[float]:
  with _lock:
    return _latest.get("sol/usd")


def get_latest_xrp_usd() -> Optional[float]:
  with _lock:
    return _latest.get("xrp/usd")


def get_btc_move_60s() -> Optional[float]:
  """
  Return BTC price change (as decimal, e.g. 0.003 = 0.3%) over last 60 seconds.
  Returns None if insufficient data.
  """
  return _move_60s("btc/usd")


def _move_60s(symbol: str) -> Optional[float]:
  now_ms = int(time.time() * 1000)
  cutoff_ms = now_ms - 60 * 1000
  with _lock:
    buf = _buffers[symbol]
    latest_v = _latest.get(symbol)
    if not buf or latest_v is None:
      return None
    price_at_cutoff = None
    for t, v in buf:
      if t <= cutoff_ms:
        price_at_cutoff = v
      else:
        break
    if price_at_cutoff is None or price_at_cutoff <= 0:
      return None
    return (latest_v - price_at_cutoff) / price_at_cutoff


def _price_at_timestamp(symbol: str, ts_unix_seconds: int) -> Optional[float]:
  """
  Return price at the given Unix timestamp (seconds): last tick with timestamp <= T.
  Returns None if no data for this symbol yet. For a new window (ts within
  RECENT_WINDOW_SEC of now) with no tick at or before ts, use the first tick in buffer.
  """
  if ts_unix_seconds <= 0:
    return None
  now_sec = int(time.time())
  with _lock:
    cache = _start_price_caches[symbol]
    buf = _buffers[symbol]
    cached = cache.get(ts_unix_seconds)
    if cached is not None:
      return cached
    if not buf:
      return None
    ts_ms = ts_unix_seconds * 1000
    last_at_or_before = None
    for t, v in buf:
      if t > ts_ms:
        break
      last_at_or_before = v
    if last_at_or_before is not None:
      cache[ts_unix_seconds] = last_at_or_before
    else:
      if now_sec - ts_unix_seconds <= _RECENT_WINDOW_SEC:
        first_v = buf[0][1]
        cache[ts_unix_seconds] = first_v
        last_at_or_before = first_v
    cutoff = now_sec - _START_PRICE_CACHE_MAX_AGE_SEC
    to_drop = [k for k in cache if k < cutoff]
    for k in to_drop:
      del cache[k]
  return last_at_or_before


def get_btc_at_timestamp(ts_unix_seconds: int) -> Optional[float]:
  """BTC price at Unix timestamp (seconds). None if no data yet."""
  return _price_at_timestamp("btc/usd", ts_unix_seconds)


def get_eth_at_timestamp(ts_unix_seconds: int) -> Optional[float]:
  """ETH price at Unix timestamp (seconds). None if no data yet."""
  return _price_at_timestamp("eth/usd", ts_unix_seconds)


def get_sol_at_timestamp(ts_unix_seconds: int) -> Optional[float]:
  """SOL price at Unix timestamp (seconds). None if no data yet."""
  return _price_at_timestamp("sol/usd", ts_unix_seconds)


def get_xrp_at_timestamp(ts_unix_seconds: int) -> Optional[float]:
  """XRP price at Unix timestamp (seconds). None if no data yet."""
  return _price_at_timestamp("xrp/usd", ts_unix_seconds)
