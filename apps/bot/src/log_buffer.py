"""Log buffer for dashboard: captures loguru output, flushes to Convex every 20s (up to 100 lines per batch)."""
import threading
import time
from datetime import datetime, timezone
from loguru import logger

from src.config import CONVEX_URL
from src.database import _get_client

_BUFFER: list[dict] = []
_BUFFER_LOCK = threading.Lock()
_MAX_BUFFER = 500
_FLUSH_INTERVAL = 20
_flush_thread: threading.Thread | None = None
_flush_stop = threading.Event()


def _level_to_dashboard(level_name: str) -> str:
  """Map loguru level to dashboard LogLevel (INFO, WARN, ERROR)."""
  name = (level_name or "").upper()
  if "ERROR" in name or "CRITICAL" in name:
    return "ERROR"
  if "WARN" in name:
    return "WARN"
  return "INFO"


def _format_timestamp(record) -> str:
  """Format record time as YYYY-MM-DD HH:MM:SS."""
  t = record.get("time")
  if t is None:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
  if hasattr(t, "strftime"):
    return t.strftime("%Y-%m-%d %H:%M:%S")
  if isinstance(t, (int, float)):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
  return str(t)[:19]


def _sink(message) -> None:
  """Loguru sink: append to buffer. Cap size to avoid unbounded growth."""
  record = message.record
  level_obj = record.get("level")
  level_name = getattr(level_obj, "name", "INFO") if level_obj else "INFO"
  entry = {
    "timestamp": _format_timestamp(record),
    "level": _level_to_dashboard(level_name),
    "message": record.get("message", ""),
  }
  with _BUFFER_LOCK:
    _BUFFER.append(entry)
    if len(_BUFFER) > _MAX_BUFFER:
      del _BUFFER[: len(_BUFFER) - _MAX_BUFFER]


def _flush() -> None:
  """Take up to 100 entries from buffer and send to Convex."""
  client = _get_client()
  if not client:
    return
  with _BUFFER_LOCK:
    batch = _BUFFER[:100]
    del _BUFFER[:100]
  if not batch:
    return
  try:
    client.mutation("logBatches:insertBatch", {"entries": batch})
  except Exception as e:
    logger.debug(f"Log batch flush failed: {e}")


def _flush_loop() -> None:
  """Background thread: flush every 20 seconds."""
  while not _flush_stop.wait(_FLUSH_INTERVAL):
    _flush()


def start_log_buffer() -> None:
  """Register loguru sink and start flush thread. Call after init_db."""
  global _flush_thread
  if not CONVEX_URL:
    return
  logger.add(_sink, format="{message}")
  _flush_stop.clear()
  _flush_thread = threading.Thread(target=_flush_loop, daemon=True)
  _flush_thread.start()


def stop_log_buffer() -> None:
  """Stop flush thread and do final flush."""
  global _flush_thread
  _flush_stop.set()
  if _flush_thread:
    _flush_thread.join(timeout=1)
    _flush_thread = None
  _flush()
