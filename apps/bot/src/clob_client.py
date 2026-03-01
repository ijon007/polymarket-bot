"""Polymarket CLOB client for market orders, trades, notifications, and balance."""
from loguru import logger

from src.config import (
    PRIVATE_KEY,
    POLYMARKET_CLOB_HOST,
    POLYMARKET_CHAIN_ID,
    POLYMARKET_SIGNATURE_TYPE,
    POLYMARKET_FUNDER_ADDRESS,
    POLYMARKET_API_KEY,
    POLYMARKET_API_SECRET,
    POLYMARKET_API_PASSPHRASE,
    POLYMARKET_MIN_ORDER_SIZE_SHARES,
)

_clob_client = None


def _get_client():
    """Lazy-init L2 CLOB client. Returns None if PRIVATE_KEY not set."""
    global _clob_client
    if not PRIVATE_KEY:
        return None
    if _clob_client is None:
        try:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import ApiCreds

            kwargs = {
                "host": POLYMARKET_CLOB_HOST,
                "key": PRIVATE_KEY,
                "chain_id": POLYMARKET_CHAIN_ID,
                "signature_type": POLYMARKET_SIGNATURE_TYPE,
            }
            if POLYMARKET_FUNDER_ADDRESS:
                kwargs["funder"] = POLYMARKET_FUNDER_ADDRESS

            _clob_client = ClobClient(**kwargs)

            if POLYMARKET_API_KEY and POLYMARKET_API_SECRET and POLYMARKET_API_PASSPHRASE:
                creds = ApiCreds(
                    api_key=POLYMARKET_API_KEY,
                    api_secret=POLYMARKET_API_SECRET,
                    api_passphrase=POLYMARKET_API_PASSPHRASE,
                )
                _clob_client.set_api_creds(creds)
            else:
                creds = _clob_client.create_or_derive_api_creds()
                _clob_client.set_api_creds(creds)
        except Exception as e:
            logger.error(f"CLOB client init failed: {e}")
            return None
    return _clob_client


def place_market_order(
    token_id: str,
    amount_dollars: float,
    side: str = "BUY",
    price_hint: float = None,
    price: float = None,
):
    """
    Place a market order. For BUY, amount is dollar amount (e.g. 10 = $10).
    Polymarket requires size in shares >= POLYMARKET_MIN_ORDER_SIZE_SHARES; pass price_hint
    so we can reject too-small orders (executor passes signal price and clamps amount).
    Pass price (worst-price limit) to bypass orderbook calc when book is empty; otherwise
    client calculates from orderbook and raises "no match" if no liquidity.
    Returns dict with success, orderID, errorMsg, transactionsHashes, status, etc.
    """
    client = _get_client()
    if not client:
        return {"success": False, "errorMsg": "CLOB client not initialized (PRIVATE_KEY?)"}

    if price_hint is not None and price_hint > 0 and price_hint <= 1:
        min_dollars = POLYMARKET_MIN_ORDER_SIZE_SHARES * price_hint
        if amount_dollars < min_dollars:
            return {
                "success": False,
                "errorMsg": f"Market order ${amount_dollars:.2f} would be < {POLYMARKET_MIN_ORDER_SIZE_SHARES} shares at price {price_hint}. Need >= ${min_dollars:.2f}.",
            }

    # Use provided price as worst-price limit to avoid "no match" when orderbook empty
    worst_price = None
    if price is not None and 0 < price <= 1:
        worst_price = price

    try:
        from py_clob_client.clob_types import MarketOrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY, SELL

        side_const = BUY if str(side).upper() == "BUY" else SELL
        mo = MarketOrderArgs(
            token_id=token_id,
            amount=amount_dollars,
            side=side_const,
            order_type=OrderType.FAK,
            price=worst_price if worst_price is not None else 0,
        )
        signed = client.create_market_order(mo)
        resp = client.post_order(signed, OrderType.FAK)
        return resp if isinstance(resp, dict) else {"success": True, **resp}
    except Exception as e:
        err = str(e).lower()
        if "no match" in err or "no orderbook" in err:
            logger.warning(f"place_market_order: no liquidity ({e})")
        elif "l2_auth_not_available" in err or "auth" in err:
            logger.warning("CLOB auth error - try deriving API key: create_or_derive_api_creds()")
        elif "insufficient balance" in err or "balance" in err:
            logger.error("Insufficient balance - fund your Polymarket wallet")
        elif "allowance" in err or "approve" in err:
            logger.error("Insufficient allowance - approve exchange on Polymarket UI or setApprovalForAll")
        else:
            logger.exception(f"place_market_order failed: {e}")
        return {"success": False, "errorMsg": str(e)}


def place_limit_order(
    token_id: str,
    price: float,
    amount_dollars: float,
    side: str = "BUY",
    tick_size: str = "0.01",
    neg_risk: bool = False,
):
    """
    Place a GTC limit order. For BUY: size in shares = amount_dollars / price.
    Use when FAK/FOK market order fails with "no match" (thin/empty orderbook).
    Returns dict with success, orderID, errorMsg, etc.
    """
    client = _get_client()
    if not client:
        return {"success": False, "errorMsg": "CLOB client not initialized (PRIVATE_KEY?)"}
    if price <= 0 or price > 1:
        return {"success": False, "errorMsg": "Limit price must be in (0, 1]"}
    size_shares = amount_dollars / price
    size_shares = round(size_shares, 2)
    if size_shares <= 0:
        return {"success": False, "errorMsg": "Order size would be zero"}
    if size_shares < POLYMARKET_MIN_ORDER_SIZE_SHARES:
        return {
            "success": False,
            "errorMsg": f"Order size ({size_shares}) below Polymarket minimum ({POLYMARKET_MIN_ORDER_SIZE_SHARES} shares). Need at least ${POLYMARKET_MIN_ORDER_SIZE_SHARES * price:.2f} at this price.",
        }

    try:
        from py_clob_client.clob_types import OrderArgs, OrderType, PartialCreateOrderOptions
        from py_clob_client.order_builder.constants import BUY, SELL

        side_const = BUY if str(side).upper() == "BUY" else SELL
        order_args = OrderArgs(
            token_id=token_id,
            price=round(price, 2),
            size=size_shares,
            side=side_const,
        )
        options = PartialCreateOrderOptions(tick_size=tick_size, neg_risk=neg_risk)
        resp = client.create_and_post_order(order_args, options)
        return resp if isinstance(resp, dict) else {"success": True, **resp}
    except Exception as e:
        err = str(e).lower()
        if "l2_auth_not_available" in err or "auth" in err:
            logger.warning("CLOB auth error - try deriving API key")
        elif "insufficient balance" in err or "balance" in err:
            logger.error("Insufficient balance - fund your Polymarket wallet")
        elif "allowance" in err or "approve" in err:
            logger.error("Insufficient allowance - approve exchange on Polymarket UI")
        logger.exception(f"place_limit_order failed: {e}")
        return {"success": False, "errorMsg": str(e)}


def get_trades(market: str = None, asset_id: str = None, before: int = None, after: int = None):
    """Get trades for the authenticated user. market = condition_id."""
    client = _get_client()
    if not client:
        return []

    try:
        from py_clob_client.clob_types import TradeParams

        params = TradeParams(
            market=market or None,
            asset_id=asset_id or None,
            before=before,
            after=after,
        )
        trades = client.get_trades(params)
        return trades if trades else []
    except Exception as e:
        logger.debug(f"get_trades failed: {e}")
        return []


def get_notifications():
    """Get L2 notifications. Type 4 = Market Resolved."""
    client = _get_client()
    if not client:
        return []

    try:
        notifs = client.get_notifications()
        return notifs if notifs else []
    except Exception as e:
        logger.debug(f"get_notifications failed: {e}")
        return []


def drop_notifications(ids):
    """Mark notifications as read. ids: list of notification id (int or str)."""
    client = _get_client()
    if not client:
        return

    try:
        from py_clob_client.clob_types import DropNotificationParams

        id_strs = [str(i) for i in ids]
        client.drop_notifications(DropNotificationParams(ids=id_strs))
    except Exception as e:
        logger.debug(f"drop_notifications failed: {e}")


# USDC (and USDC.e) on Polygon use 6 decimals. CLOB returns balance/allowance as raw string.
USDC_DECIMALS = 6


def get_balance_allowance(asset_type: str = "COLLATERAL", token_id: str = None):
    """
    Get balance and allowance. asset_type: COLLATERAL (USDC) or CONDITIONAL.
    Returns dict with balance (in dollars), allowance (in dollars), and raw balance/allowance,
    or None on error. CLOB returns balance/allowance as string in raw units (6 decimals for USDC).
    """
    client = _get_client()
    if not client:
        return None

    try:
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType

        at = AssetType.COLLATERAL if asset_type == "COLLATERAL" else AssetType.CONDITIONAL
        params = BalanceAllowanceParams(asset_type=at)
        if token_id:
            params.token_id = token_id
        result = client.get_balance_allowance(params)
        if result is None:
            return None
        # API returns dict with balance, allowance as strings (raw USDC units, 6 decimals)
        if not isinstance(result, dict):
            result = getattr(result, "__dict__", None) or {}
        raw_balance = result.get("balance") or result.get("balance_allowance") or 0
        raw_allowance = result.get("allowance") or 0
        try:
            bal = float(raw_balance)
            allow = float(raw_allowance)
        except (TypeError, ValueError):
            return {"balance": 0.0, "allowance": 0.0}
        if asset_type == "COLLATERAL":
            bal /= 10**USDC_DECIMALS
            allow /= 10**USDC_DECIMALS
        return {"balance": bal, "allowance": allow}
    except Exception as e:
        logger.debug(f"get_balance_allowance failed: {e}")
        return None
