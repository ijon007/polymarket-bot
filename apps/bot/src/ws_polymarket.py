"""
Polymarket WebSocket client for order book (15-min signal engine).
Updates in-memory state on each book message. Used for imbalance only.
"""
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
  bids: List[OrderLevel] = None
  asks: List[OrderLevel] = None
  updated_at: float = 0.0

  def __post_init__(self):
    if self.bids is None:
      self.bids = []
    if self.asks is None:
      self.asks = []


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


_lock = threading.Lock()
_yes_book: Optional[TokenBook] = None
_no_book: Optional[TokenBook] = None
_stale = True
_ws: Optional[Any] = None
_thread: Optional[threading.Thread] = None
_stop = threading.Event()
_subscribed_ids: List[str] = []


def _on_message(_: Any, message: str) -> None:
  global _yes_book, _no_book, _stale
  if not message or not message.strip():
    return
  if message == "PONG":
    return
  try:
    data = json.loads(message)
    if not isinstance(data, dict):
      return
    if data.get("event_type") != "book":
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
      if len(_subscribed_ids) >= 1 and asset_id == _subscribed_ids[0]:
        _yes_book = new_book
      elif len(_subscribed_ids) >= 2 and asset_id == _subscribed_ids[1]:
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
  global _thread, _subscribed_ids, _yes_book, _no_book
  _subscribed_ids = [yes_token_id, no_token_id]
  _yes_book = None
  _no_book = None
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


def get_best_asks() -> tuple[Optional[float], Optional[float]]:
  """Return (yes_ask, no_ask)."""
  with _lock:
    yes = _yes_book.best_ask if _yes_book else None
    no = _no_book.best_ask if _no_book else None
  return yes, no


def get_imbalance_data() -> tuple[float, float, bool]:
  """
  Return (bid_volume, ask_volume, stale) for top 5 levels aggregated across YES+NO.
  Imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol). Positive = more bid pressure.
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
