"""Order execution (paper mode: log and persist to Neon)."""

from datetime import datetime
from typing import Any

from loguru import logger

from src.data.database import save_opportunity, save_trade
from src.risk.position_sizing import calculate_position_size
from src.risk import risk_limits
from src.utils.config import BANKROLL, PAPER_MODE


def _implied_prob(market: Any) -> float:
    """Yes price as decimal 0-1."""
    y = getattr(market, "yes_price", 0) or 0
    return y / 100.0 if y > 1 else y


def execute_trade(market: Any, signal: dict) -> bool:
    """
    Execute or log a trade from a logic signal. Uses position_sizing and risk_limits.
    Paper mode: save_trade + save_opportunity and return True.
    """
    try:
        if not risk_limits.check_limits():
            return False
        edge = signal.get("edge", 0.0)
        confidence = signal.get("confidence", 0.5)
        implied = _implied_prob(market)
        size = calculate_position_size(
            edge=edge,
            confidence=confidence,
            bankroll=BANKROLL,
            trade_type="logic",
            implied_prob=implied,
        )
        if size <= 0:
            return False

        trade = {
            "market_ticker": getattr(market, "ticker", "") or "",
            "side": signal["action"].replace("bet_", "").upper(),
            "price": signal.get("price", 0),
            "size": size,
            "reason": signal.get("reason", ""),
            "expected_profit": signal.get("expected_profit", 0),
            "executed_at": datetime.utcnow(),
            "status": "paper" if PAPER_MODE else "executed",
        }
        if PAPER_MODE:
            logger.info(f"PAPER TRADE: {trade}")
            save_trade(trade)
            save_opportunity(
                market_ticker=trade["market_ticker"],
                type_="logic",
                edge=edge,
                confidence=confidence,
            )
            return True
        logger.warning("Real trading not implemented yet")
        return False
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        return False


def execute_arb(market: Any, arb_signal: dict) -> bool:
    """Execute internal arbitrage (paper: log two orders YES + NO and save)."""
    try:
        if not risk_limits.check_limits():
            return False
        size = calculate_position_size(
            edge=arb_signal.get("expected_profit", 0) / (arb_signal.get("total_cost") or 1),
            confidence=arb_signal.get("confidence", 0.99),
            bankroll=BANKROLL,
            trade_type="internal_arb",
            implied_prob=arb_signal.get("yes_price", 0.5),
        )
        if size <= 0:
            return False
        ticker = getattr(market, "ticker", "") or ""
        if PAPER_MODE:
            for side, price in [("YES", arb_signal["yes_price"]), ("NO", arb_signal["no_price"])]:
                trade = {
                    "market_ticker": ticker,
                    "side": side,
                    "price": price,
                    "size": size,
                    "reason": f"internal_arb {arb_signal.get('profit_pct', 0):.2f}%",
                    "expected_profit": arb_signal.get("expected_profit", 0) / 2,
                    "executed_at": datetime.utcnow(),
                    "status": "paper",
                }
                save_trade(trade)
            save_opportunity(ticker, "arb", arb_signal.get("expected_profit"), arb_signal.get("confidence"))
            logger.info(f"PAPER ARB: {ticker} YES@{arb_signal['yes_price']} NO@{arb_signal['no_price']} size={size}")
            return True
        logger.warning("Real trading not implemented yet")
        return False
    except Exception as e:
        logger.error(f"Error executing arb: {e}")
        return False


def execute_combo(combo_signal: dict) -> bool:
    """Execute combinatorial arbitrage (paper: log orders across markets)."""
    try:
        if not risk_limits.check_limits():
            return False
        markets = combo_signal.get("markets", [])
        prices = combo_signal.get("prices", [])
        if len(markets) != len(prices):
            return False
        # Size per market: total budget split by number of legs
        total_cost = combo_signal.get("total_cost", 1.0)
        profit = combo_signal.get("expected_profit", 0)
        confidence = combo_signal.get("confidence", 0.95)
        edge = profit / total_cost if total_cost else 0
        size = calculate_position_size(
            edge=edge,
            confidence=confidence,
            bankroll=BANKROLL,
            trade_type="combo",
            implied_prob=1.0 / len(markets) if markets else 0.5,
        )
        if size <= 0:
            return False
        per_leg = size / len(markets) if markets else 0
        if PAPER_MODE:
            for ticker, price in zip(markets, prices):
                trade = {
                    "market_ticker": ticker,
                    "side": "YES",
                    "price": price,
                    "size": per_leg,
                    "reason": "combinatorial_arb",
                    "expected_profit": profit / len(markets),
                    "executed_at": datetime.utcnow(),
                    "status": "paper",
                }
                save_trade(trade)
            save_opportunity(markets[0] if markets else "", "combo", profit, confidence)
            logger.info(f"PAPER COMBO: {markets} profit={profit:.4f}")
            return True
        logger.warning("Real trading not implemented yet")
        return False
    except Exception as e:
        logger.error(f"Error executing combo: {e}")
        return False
