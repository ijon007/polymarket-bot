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


def place_market_order(token_id: str, amount_dollars: float, side: str = "BUY"):
    """
    Place a market order. For BUY, amount is dollar amount (e.g. 10 = $10).
    Returns dict with success, orderID, errorMsg, transactionsHashes, status, etc.
    """
    client = _get_client()
    if not client:
        return {"success": False, "errorMsg": "CLOB client not initialized (PRIVATE_KEY?)"}

    try:
        from py_clob_client.clob_types import MarketOrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY, SELL

        side_const = BUY if str(side).upper() == "BUY" else SELL
        mo = MarketOrderArgs(
            token_id=token_id,
            amount=amount_dollars,
            side=side_const,
            order_type=OrderType.FOK,
        )
        signed = client.create_market_order(mo)
        resp = client.post_order(signed, OrderType.FOK)
        return resp if isinstance(resp, dict) else {"success": True, **resp}
    except Exception as e:
        err = str(e).lower()
        if "l2_auth_not_available" in err or "auth" in err:
            logger.warning("CLOB auth error - try deriving API key: create_or_derive_api_creds()")
        elif "insufficient balance" in err or "balance" in err:
            logger.error("Insufficient balance - fund your Polymarket wallet")
        elif "allowance" in err or "approve" in err:
            logger.error("Insufficient allowance - approve exchange on Polymarket UI or setApprovalForAll")
        logger.exception(f"place_market_order failed: {e}")
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


def get_balance_allowance(asset_type: str = "COLLATERAL", token_id: str = None):
    """
    Get balance and allowance. asset_type: COLLATERAL (USDC) or CONDITIONAL.
    Returns dict with balance, allowance or None on error.
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
        return result
    except Exception as e:
        logger.debug(f"get_balance_allowance failed: {e}")
        return None
