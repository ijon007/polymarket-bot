"""
Polymarket WebSocket client for order book and whale detection.
Used only by the 15-min signal engine. Updates in-memory state on each book message.
"""
import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
  import websocket
except ImportError:
  websocket = None

from src.config import POLYMARKET_WS_URL

_PING_INTERVAL = 20
_PING_TIMEOUT = 10
_RECONNECT_DELAY = 5
_MAX_RECONNECT_DELAY = 60
_reconnect_delay = _RECONNECT_DELAY
_SPOOF_WINDOW_SEC = 10
_LAYERING_LEVELS = 5
_LAYERING_SIZE_THRESHOLD = 50.0
_TOP_LEVELS = 5


@dataclass
class OrderLevel:
  price: float
  size: float


@dataclass
class TokenBook:
  asset_id: str
  best_bid: Optional[float] = None
  best_ask: Optional[float] = None
  bids: List[OrderLevel] = field(default_factory=list)
  asks: List[OrderLevel] = field(default_factory=list)
  updated_at: float = 0.0


@dataclass
class WhaleSignal:
  signal_type: str  # iceberg, sweep, spoof, layering
  direction: str  # YES or NO
  opposite: bool  # True for spoof -> trade opposite
  timestamp: float = 0.0


def _parse_levels(raw: List[Dict[str, Any]]) -> List[OrderLevel]:
  out: List[OrderLevel] = []
  for item in raw:
    try:
      p = float(item.get("price", 0))
      s = float(item.get("size", 0))
      if p > 0 and s > 0:
        out.append(OrderLevel(price=p, size=s))
    except (TypeError, ValueError):
      continue
  return out


# In-memory state (thread-safe via lock)
_lock = threading.Lock()
_yes_book: Optional[TokenBook] = None
_no_book: Optional[TokenBook] = None
_whale_signals: List[WhaleSignal] = []
_stale = True
_prev_yes: Optional[TokenBook] = None
_prev_no: Optional[TokenBook] = None
_level_refill_count: Dict[str, int] = {}  # "asset_id:price" -> refill count
_large_order_seen: Dict[str, float] = {}  # "asset_id:price" -> timestamp
_ws: Optional[Any] = None
_thread: Optional[threading.Thread] = None
_stop = threading.Event()
_subscribed_ids: List[str] = []


def _detect_whale(
  asset_id: str,
  side: str,
  new_book: TokenBook,
  prev_book: Optional[TokenBook],
) -> Optional[WhaleSignal]:
  """Run whale detection. Returns signal if detected."""
  now = time.time()

  # Layering: 5+ levels above size threshold on one side
  levels = new_book.asks if side == "ask" else new_book.bids
  big_levels = [l for l in levels[: _LAYERING_LEVELS + 2] if l.size >= _LAYERING_SIZE_THRESHOLD]
  if len(big_levels) >= _LAYERING_LEVELS:
    return WhaleSignal(
      signal_type="layering",
      direction="YES" if asset_id == _subscribed_ids[0] else "NO",
      opposite=False,
      timestamp=now,
    )

  if prev_book is None:
    return None

  prev_levels = prev_book.asks if side == "ask" else prev_book.bids
  new_levels = new_book.asks if side == "ask" else new_book.bids

  # Sweep: 3+ levels consumed at once (size dropped significantly)
  consumed = 0
  for i, nl in enumerate(new_levels[:5]):
    if i >= len(prev_levels):
      break
    pl = prev_levels[i]
    if pl.price == nl.price and nl.size < pl.size * 0.5:
      consumed += 1
  if consumed >= 3:
    return WhaleSignal(
      signal_type="sweep",
      direction="YES" if asset_id == _subscribed_ids[0] else "NO",
      opposite=False,
      timestamp=now,
    )

  # Iceberg: same level refills (size increases after drop)
  for i, nl in enumerate(new_levels[:5]):
    if i >= len(prev_levels):
      continue
    pl = prev_levels[i]
    key = f"{asset_id}:{pl.price}"
    if pl.price == nl.price:
      if nl.size > pl.size * 1.1:
        _level_refill_count[key] = _level_refill_count.get(key, 0) + 1
        if _level_refill_count[key] >= 3:
          return WhaleSignal(
            signal_type="iceberg",
            direction="YES" if asset_id == _subscribed_ids[0] else "NO",
            opposite=False,
            timestamp=now,
          )
      else:
        _level_refill_count[key] = 0

  # Spoof: large order appears then disappears in <10s
  for nl in new_levels[:3]:
    if nl.size >= _LAYERING_SIZE_THRESHOLD:
      key = f"{asset_id}:{nl.price}"
      _large_order_seen[key] = now
  for pk, pt in list(_large_order_seen.items()):
    if now - pt > _SPOOF_WINDOW_SEC:
      del _large_order_seen[pk]
    elif pk.startswith(asset_id + ":"):
      # Check if this level disappeared
      still_there = any(
        abs(l.price - float(pk.split(":")[1])) < 0.001 and l.size >= _LAYERING_SIZE_THRESHOLD
        for l in new_levels[:5]
      )
      if not still_there and now - pt < _SPOOF_WINDOW_SEC:
        del _large_order_seen[pk]
        return WhaleSignal(
          signal_type="spoof",
          direction="YES" if asset_id == _subscribed_ids[0] else "NO",
          opposite=True,
          timestamp=now,
        )

  return None


def _on_message(_: Any, message: str) -> None:
  global _yes_book, _no_book, _whale_signals, _stale, _prev_yes, _prev_no
  if not message or not message.strip():
    return
  if message == "PONG":
    return
  try:
    data = json.loads(message)
    if not isinstance(data, dict):
      return
    event_type = data.get("event_type")
    if event_type != "book":
      return

    asset_id = str(data.get("asset_id", ""))
    bids_raw = data.get("bids", data.get("buys", []))
    asks_raw = data.get("asks", data.get("sells", []))
    bids = _parse_levels(bids_raw)
    asks = _parse_levels(asks_raw)

    best_bid = bids[0].price if bids else None
    best_ask = asks[0].price if asks else None

    new_book = TokenBook(
      asset_id=asset_id,
      best_bid=best_bid,
      best_ask=best_ask,
      bids=bids[:_TOP_LEVELS + 2],
      asks=asks[:_TOP_LEVELS + 2],
      updated_at=time.time(),
    )

    with _lock:
      is_yes = len(_subscribed_ids) >= 1 and asset_id == _subscribed_ids[0]
      is_no = len(_subscribed_ids) >= 2 and asset_id == _subscribed_ids[1]
      prev = _prev_yes if is_yes else (_prev_no if is_no else None)
      if is_yes or is_no:
        sig = _detect_whale(asset_id, "ask", new_book, prev)
        if sig:
          _whale_signals.append(sig)
          if len(_whale_signals) > 20:
            _whale_signals.pop(0)
      if is_yes:
        _prev_yes = _yes_book
        _yes_book = new_book
      elif is_no:
        _prev_no = _no_book
        _no_book = new_book
      _stale = False
  except Exception as e:
    logger.debug(f"Polymarket WS parse error: {e}")


def _on_error(_: Any, error: Exception) -> None:
  err_str = str(error).lower()
  if "getaddrinfo failed" in err_str or "11001" in err_str:
    logger.warning("Polymarket WS DNS/network error")
  else:
    logger.warning(f"Polymarket WS error: {error}")


def _on_close(_: Any, close_status_code: int, close_msg: str) -> None:
  global _stale
  logger.info(f"Polymarket WS closed: {close_status_code} {close_msg}")
  with _lock:
    _stale = True


def _on_open(ws: Any) -> None:
  global _reconnect_delay
  _reconnect_delay = _RECONNECT_DELAY
  if _subscribed_ids:
    sub = {"assets_ids": _subscribed_ids, "type": "market"}
    ws.send(json.dumps(sub))
    logger.info(f"Polymarket WS subscribed to {len(_subscribed_ids)} assets")
  else:
    logger.warning("Polymarket WS opened but no asset IDs to subscribe")
  t = threading.Thread(target=_ping_loop, args=(ws,), daemon=True)
  t.start()


def _ping_loop(ws: Any) -> None:
  while not _stop.is_set() and ws:
    try:
      ws.send("PING")
    except Exception:
      break
    _stop.wait(_PING_INTERVAL)


def _run_loop() -> None:
  global _ws, _reconnect_delay
  while not _stop.is_set():
    try:
      if websocket is None:
        logger.error("websocket-client not installed; pip install websocket-client")
        break
      base = POLYMARKET_WS_URL.rstrip("/")
      url = f"{base}/ws/market" if "/ws/" not in base else base
      _ws = websocket.WebSocketApp(
        url,
        on_message=_on_message,
        on_error=_on_error,
        on_close=_on_close,
        on_open=_on_open,
      )
      _ws.run_forever(ping_interval=_PING_INTERVAL, ping_timeout=_PING_TIMEOUT)
    except Exception as e:
      logger.warning(f"Polymarket WS connection failed: {e}")
    if _stop.is_set():
      break
    delay = _reconnect_delay
    time.sleep(delay)
    _reconnect_delay = min(_reconnect_delay * 1.5, _MAX_RECONNECT_DELAY)
  _ws = None


def start(yes_token_id: str, no_token_id: str) -> None:
  """Start Polymarket WS and subscribe to YES/NO token order books."""
  global _thread, _subscribed_ids, _yes_book, _no_book, _prev_yes, _prev_no
  _subscribed_ids = [yes_token_id, no_token_id]
  _yes_book = None
  _no_book = None
  _prev_yes = None
  _prev_no = None
  if _thread is not None and _thread.is_alive():
    return
  _stop.clear()
  _thread = threading.Thread(target=_run_loop, daemon=True)
  _thread.start()
  logger.info("Polymarket WS client started")


def stop() -> None:
  """Stop the WebSocket client."""
  global _ws
  _stop.set()
  if _ws:
    try:
      _ws.close()
    except Exception:
      pass
    _ws = None


def get_order_book_state() -> Tuple[
  Optional[float], Optional[float],
  List[OrderLevel], List[OrderLevel],
  List[OrderLevel], List[OrderLevel],
  List[WhaleSignal], bool,
]:
  """
  Return (yes_ask, no_ask, yes_asks, no_asks, yes_bids, no_bids, whale_signals, stale).
  """
  with _lock:
    stale = _stale
    signals = list(_whale_signals)
    yes_ask = _yes_book.best_ask if _yes_book else None
    no_ask = _no_book.best_ask if _no_book else None
    yes_asks = list(_yes_book.asks[:_TOP_LEVELS]) if _yes_book else []
    no_asks = list(_no_book.asks[:_TOP_LEVELS]) if _no_book else []
    yes_bids = list(_yes_book.bids[:_TOP_LEVELS]) if _yes_book else []
    no_bids = list(_no_book.bids[:_TOP_LEVELS]) if _no_book else []
  return yes_ask, no_ask, yes_asks, no_asks, yes_bids, no_bids, signals, stale


def get_best_asks() -> Tuple[Optional[float], Optional[float]]:
  """Convenience: return (yes_ask, no_ask) only."""
  with _lock:
    yes = _yes_book.best_ask if _yes_book else None
    no = _no_book.best_ask if _no_book else None
  return yes, no


def get_imbalance_data() -> Tuple[float, float, bool]:
  """
  Return (bid_volume, ask_volume, stale) for top 5 levels aggregated across YES+NO.
  bid_volume = sum of size at top 5 bid levels (YES bids + NO bids, but for binary
  YES bid ~ buy YES, NO bid ~ buy NO; we want total liquidity each side).
  For a single market with YES and NO tokens: bids on YES = people selling YES (bearish),
  asks on YES = people selling YES (or we buy YES). Simpler: use YES book + NO book.
  Imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol). Bids = buy pressure, asks = sell.
  """
  with _lock:
    stale = _stale
    bid_vol = 0.0
    ask_vol = 0.0
    if _yes_book:
      for l in _yes_book.bids[:_TOP_LEVELS]:
        bid_vol += l.size
      for l in _yes_book.asks[:_TOP_LEVELS]:
        ask_vol += l.size
    if _no_book:
      for l in _no_book.bids[:_TOP_LEVELS]:
        bid_vol += l.size
      for l in _no_book.asks[:_TOP_LEVELS]:
        ask_vol += l.size
  return bid_vol, ask_vol, stale


def get_whale_signals() -> List[WhaleSignal]:
  """Return recent whale signals (caller consumes/copies)."""
  with _lock:
    return list(_whale_signals)
