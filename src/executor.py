from datetime import datetime
from loguru import logger
from src.database import log_trade
from src.config import PAPER_MODE


def execute_trade(market, signal):
    """
    Execute trade based on signal.

    Handles special cases:
    - action='bet_both': Execute arbitrage (buy YES and NO)
    - action='bet_yes': Buy YES
    - action='bet_no': Buy NO
    """
    if not PAPER_MODE:
        logger.warning("Real trading not implemented yet")
        return False

    # Handle arbitrage (bet both sides)
    if signal["action"] == "bet_both":
        trade_data = {
            "condition_id": market["condition_id"],
            "question": market["question"],
            "strategy": signal["strategy"],
            "action": "ARBITRAGE",
            "price": None,
            "yes_price": signal["yes_price"],
            "no_price": signal["no_price"],
            "position_size": signal["size"],
            "expected_profit": signal["expected_profit"],
            "confidence": signal["confidence"],
            "reason": signal["reason"],
            "executed_at": datetime.utcnow(),
            "status": "paper",
        }

        logger.info(
            f"PAPER TRADE [ARBITRAGE]: "
            f"Buy YES @ {signal['yes_price']:.4f} + NO @ {signal['no_price']:.4f} | "
            f"Size: ${signal['size']:.2f} | "
            f"Expected: ${signal['expected_profit']:.2f}"
        )

    # Handle directional bets
    else:
        side = "YES" if signal["action"] == "bet_yes" else "NO"

        trade_data = {
            "condition_id": market["condition_id"],
            "question": market["question"],
            "strategy": signal["strategy"],
            "action": side,
            "price": signal["price"],
            "yes_price": None,
            "no_price": None,
            "position_size": signal["size"],
            "expected_profit": signal.get("expected_profit", 0),
            "confidence": signal["confidence"],
            "reason": signal["reason"],
            "executed_at": datetime.utcnow(),
            "status": "paper",
        }

        logger.info(
            f"PAPER TRADE [{signal['strategy'].upper()}]: "
            f"Buy {side} @ {signal['price']:.4f} | "
            f"Size: ${signal['size']:.2f} | "
            f"Confidence: {signal['confidence']*100:.0f}% | "
            f"Reason: {signal['reason']}"
        )

    # Log to database
    log_trade(trade_data)
    return True
