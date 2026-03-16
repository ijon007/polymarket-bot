import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import aiohttp
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL


DATA_API_BASE = "https://data-api.polymarket.com"
CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137


@dataclass
class Config:
    private_key: str
    target_wallet: str
    copy_ratio: float
    max_bet: float
    poll_interval: float
    tg_token: Optional[str]
    tg_chat: Optional[str]


def load_config() -> Config:
    # Prefer local env for this app if present, then fall back to parent/root .env files
    load_dotenv(dotenv_path=".env.local", override=False)
    load_dotenv(override=False)

    private_key = os.getenv("PRIVATE_KEY")
    target_wallet = os.getenv("TARGET_WALLET")
    copy_ratio_str = os.getenv("COPY_RATIO")
    max_bet_str = os.getenv("MAX_BET")
    poll_interval_str = os.getenv("POLL_INTERVAL")
    tg_token = os.getenv("TG_TOKEN")
    tg_chat = os.getenv("TG_CHAT")

    if not private_key:
        raise SystemExit("❌ PRIVATE_KEY is required")
    if not target_wallet:
        raise SystemExit("❌ TARGET_WALLET is required")
    if copy_ratio_str is None:
        raise SystemExit("❌ COPY_RATIO is required")
    if max_bet_str is None:
        raise SystemExit("❌ MAX_BET is required")
    if poll_interval_str is None:
        raise SystemExit("❌ POLL_INTERVAL is required")

    try:
        copy_ratio = float(copy_ratio_str)
    except ValueError:
        raise SystemExit("❌ COPY_RATIO must be a float")

    try:
        max_bet = float(max_bet_str)
    except ValueError:
        raise SystemExit("❌ MAX_BET must be a float")

    try:
        poll_interval = float(poll_interval_str)
    except ValueError:
        raise SystemExit("❌ POLL_INTERVAL must be a float (seconds)")

    if copy_ratio <= 0:
        raise SystemExit("❌ COPY_RATIO must be > 0")
    if max_bet <= 0:
        raise SystemExit("❌ MAX_BET must be > 0")
    if poll_interval <= 0:
        raise SystemExit("❌ POLL_INTERVAL must be > 0")

    return Config(
        private_key=private_key,
        target_wallet=target_wallet,
        copy_ratio=copy_ratio,
        max_bet=max_bet,
        poll_interval=poll_interval,
        tg_token=tg_token,
        tg_chat=tg_chat,
    )


def log(msg: str) -> None:
    print(msg, flush=True)


def init_clob_client(cfg: Config) -> ClobClient:
    client = ClobClient(
        CLOB_HOST,
        key=cfg.private_key,
        chain_id=CHAIN_ID,
    )
    creds = client.create_or_derive_api_creds()
    client.set_api_creds(creds)
    return client


async def bootstrap_seen_trades(
    session: aiohttp.ClientSession, cfg: Config, seen_trade_ids: Set[str]
) -> None:
    url = f"{DATA_API_BASE}/trades"
    params = {"user": cfg.target_wallet, "limit": "20"}
    try:
        async with session.get(url, params=params, timeout=15) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except Exception as exc:
        log(f"❌ Failed to bootstrap seen trades: {exc}")
        return

    trades: List[Dict[str, Any]] = data if isinstance(data, list) else data.get("data", [])
    for trade in trades:
        tid = str(trade.get("id"))
        if tid:
            seen_trade_ids.add(tid)

    log(f"🔍 Target wallet {cfg.target_wallet} — bootstrapped {len(seen_trade_ids)} trades")


async def fetch_recent_trades(
    session: aiohttp.ClientSession, cfg: Config
) -> List[Dict[str, Any]]:
    url = f"{DATA_API_BASE}/trades"
    params = {"user": cfg.target_wallet, "limit": "20"}
    try:
        async with session.get(url, params=params, timeout=15) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except Exception as exc:
        log(f"❌ Failed to fetch recent trades: {exc}")
        return []

    trades: List[Dict[str, Any]] = data if isinstance(data, list) else data.get("data", [])
    return trades or []


async def send_telegram_alert(
    session: aiohttp.ClientSession, cfg: Config, message: str
) -> None:
    if not cfg.tg_token or not cfg.tg_chat:
        return

    url = f"https://api.telegram.org/bot{cfg.tg_token}/sendMessage"
    payload = {"chat_id": cfg.tg_chat, "text": message}
    try:
        async with session.post(url, json=payload, timeout=10) as resp:
            if resp.status != 200:
                body = await resp.text()
                log(f"❌ Telegram alert failed ({resp.status}): {body}")
    except Exception as exc:
        log(f"❌ Telegram alert error: {exc}")


def place_mirrored_order(
    client: ClobClient, cfg: Config, trade: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    try:
        token_id = str(trade.get("asset_id") or trade.get("token_id"))
        if not token_id:
            raise ValueError("missing asset_id/token_id")

        side_str = str(trade.get("side") or trade.get("direction") or "").upper()
        if side_str not in ("BUY", "SELL"):
            raise ValueError(f"unsupported side '{side_str}'")
        side = BUY if side_str == "BUY" else SELL

        price = float(trade.get("price"))
        size = float(trade.get("size"))

        scaled_size = min(size * cfg.copy_ratio, cfg.max_bet)
        if scaled_size <= 0:
            raise ValueError("scaled size <= 0, skipping")

        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=scaled_size,
            side=side,
        )

        signed = client.create_order(order_args)
        resp = client.post_order(signed, OrderType.GTC)

        market_id = str(trade.get("market_id") or trade.get("condition_id") or "")[:16]
        log(f"✅ Mirrored {side_str} {scaled_size} @ {price} on {market_id}")
        return resp
    except Exception as exc:
        log(f"❌ Failed to place mirrored order: {exc}")
        return None


async def process_new_trades(
    session: aiohttp.ClientSession,
    client: ClobClient,
    cfg: Config,
    seen_trade_ids: Set[str],
) -> None:
    trades = await fetch_recent_trades(session, cfg)
    if not trades:
        log("🔍 Poll: no trades returned from Data API")
        return

    new_count = 0
    for trade in trades:
        tid = str(trade.get("id"))
        if not tid or tid in seen_trade_ids:
            continue
        seen_trade_ids.add(tid)
        new_count += 1

        try:
            resp = place_mirrored_order(client, cfg, trade)
            if resp is not None:
                market_id = str(trade.get("market_id") or trade.get("condition_id") or "")[:16]
                side_str = str(trade.get("side") or trade.get("direction") or "").upper()
                price = trade.get("price")
                size = min(float(trade.get("size")), cfg.max_bet * cfg.copy_ratio)
                msg = f"Mirrored {side_str} {size} @ {price} on {market_id}"
                await send_telegram_alert(session, cfg, msg)
        except Exception as exc:
            log(f"❌ Error processing trade {tid}: {exc}")

    if new_count == 0:
        log("🔍 Poll: no new trades to mirror")


async def main_loop(cfg: Config) -> None:
    seen_trade_ids: Set[str] = set()

    async with aiohttp.ClientSession() as session:
        log(f"🔍 Starting copytrade bot for target wallet {cfg.target_wallet}")
        await bootstrap_seen_trades(session, cfg, seen_trade_ids)

        client = init_clob_client(cfg)

        while True:
            try:
                await process_new_trades(session, client, cfg, seen_trade_ids)
            except Exception as exc:
                log(f"❌ Main loop error: {exc}")
            await asyncio.sleep(cfg.poll_interval)


async def main() -> None:
    cfg = load_config()
    await main_loop(cfg)


if __name__ == "__main__":
    asyncio.run(main())

