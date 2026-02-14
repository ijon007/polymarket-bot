"""Logic-based trade filtering: impossible/certain events, resolution issues, LLM edge cases."""

import json
import re
from typing import Any, Optional

from loguru import logger

from src.utils.config import GROQ_API_KEY

LOGIC_RULES = {
    "impossible_events": {
        "keywords": [
            "jesus",
            "aliens",
            "supernatural",
            "miracle",
            "god",
            "heaven",
            "prophecy",
        ],
        "rule": "auto bet NO if YES < 10¢",
        "yes_threshold": 0.10,
        "action": "bet_no",
    },
    "certain_events": {
        "keywords": ["sun rise", "earth rotate", "gravity"],
        "rule": "bet YES if NO > 5¢",
        "no_threshold": 0.05,
        "action": "bet_yes",
    },
    "resolution_issues": {
        "keywords": ["by consensus", "credible sources", "generally considered"],
        "rule": "skip these markets",
        "action": "skip",
    },
    "extreme_longshots": {
        "rule": "if YES < 1¢ and no logical reason, bet NO",
        "yes_threshold": 0.01,
        "action": "bet_no",
    },
    "extreme_favorites": {
        "rule": "if YES > 99¢ and no logical certainty, bet NO",
        "yes_threshold_high": 0.99,
        "action": "bet_no",
    },
}


def _matches_keywords(text: str, keywords: list) -> bool:
    """Return True if any keyword (phrase) appears in text (case-insensitive)."""
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def _llm_evaluate(market: Any) -> Optional[dict]:
    """Call Groq LLM for edge-case evaluation; return parsed JSON or None."""
    if not GROQ_API_KEY:
        logger.debug("No GROQ_API_KEY; skipping LLM logic evaluation")
        return None
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        title = getattr(market, "title", "") or ""
        yes_price = getattr(market, "yes_price", 0) or 0
        if yes_price > 1:
            yes_price = yes_price / 100.0
        resolution = getattr(market, "resolution_criteria", "") or ""

        prompt = f"""Evaluate this prediction market for logical soundness:
Title: {title}
Current YES price: {yes_price * 100:.1f}¢
Resolution criteria: {resolution}

Questions:
Is this event physically/logically possible? (yes/no/maybe)
Has anything similar happened in recorded history? (yes/no/unknown)
Is the resolution criteria clear and verifiable? (yes/no)
What's a reasonable probability estimate? (0-100% or "unknown")
Is there an obvious logical edge here? (yes/no)
Recommendation: bet_yes/bet_no/skip

Output JSON only: {{"possible": str, "historical": str, "clear_resolution": bool, "probability": float, "has_edge": bool, "recommendation": str, "reasoning": str}}"""

        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        # Extract JSON from response (may be wrapped in markdown)
        match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        logger.debug(f"LLM logic evaluation failed: {e}")
        return None


def check_logic(market: Any) -> Optional[dict]:
    """
    Evaluate market for logic-based edge. Returns None to continue to arbitrage;
    otherwise {'action': 'bet_yes'|'bet_no'|'skip', 'confidence': float, 'reason': str, 'price': float}.
    """
    title = getattr(market, "title", "") or ""
    resolution = getattr(market, "resolution_criteria", "") or ""
    text = f"{title} {resolution}".lower()
    yes_price = getattr(market, "yes_price", 0) or 0
    no_price = getattr(market, "no_price", 0) or 0
    if yes_price > 1:
        yes_price = yes_price / 100.0
    if no_price > 1:
        no_price = no_price / 100.0

    # Resolution issues -> skip
    resolution_cfg = LOGIC_RULES["resolution_issues"]
    if _matches_keywords(text, resolution_cfg["keywords"]):
        return {
            "action": "skip",
            "confidence": 0.9,
            "reason": "Vague or consensus-based resolution criteria",
            "price": yes_price,
        }

    # Impossible events: YES < 10¢ -> bet NO
    impossible_cfg = LOGIC_RULES["impossible_events"]
    if _matches_keywords(text, impossible_cfg["keywords"]) and yes_price < impossible_cfg["yes_threshold"]:
        return {
            "action": "bet_no",
            "confidence": 0.95,
            "reason": "Impossible/supernatural event with YES < 10¢",
            "price": no_price,
            "edge": 0.10,
        }

    # Certain events: YES > 90¢ -> bet YES (spec: "bet YES if NO > 5¢" – interpret as favorable YES)
    certain_cfg = LOGIC_RULES["certain_events"]
    if _matches_keywords(text, certain_cfg["keywords"]):
        if yes_price > 0.90:
            return {
                "action": "bet_yes",
                "confidence": 0.95,
                "reason": "Certain event with YES > 90¢",
                "price": yes_price,
                "edge": 0.05,
            }
        if no_price > certain_cfg.get("no_threshold", 0.05):
            return {
                "action": "bet_yes",
                "confidence": 0.90,
                "reason": "Certain event with NO > 5¢ (underpriced YES)",
                "price": yes_price,
                "edge": 0.05,
            }

    # Extreme longshots: YES < 1¢ -> bet NO
    if yes_price < LOGIC_RULES["extreme_longshots"]["yes_threshold"]:
        return {
            "action": "bet_no",
            "confidence": 0.85,
            "reason": "Extreme longshot YES < 1¢",
            "price": no_price,
            "edge": 0.10,
        }

    # Extreme favorites: YES > 99¢ -> bet NO (spec says bet NO when no logical certainty)
    if yes_price > LOGIC_RULES["extreme_favorites"]["yes_threshold_high"]:
        return {
            "action": "bet_no",
            "confidence": 0.80,
            "reason": "Extreme favorite YES > 99¢ without logical certainty",
            "price": no_price,
            "edge": 0.05,
        }

    # Edge case: use LLM
    llm = _llm_evaluate(market)
    if llm:
        rec = (llm.get("recommendation") or "").strip().lower()
        if rec in ("bet_yes", "bet_no", "skip"):
            prob = llm.get("probability")
            if isinstance(prob, (int, float)):
                conf = min(0.95, max(0.5, abs(prob / 100.0 - 0.5) * 2))
            else:
                conf = 0.7
            reason = llm.get("reasoning") or rec
            if rec == "bet_yes":
                return {"action": "bet_yes", "confidence": conf, "reason": reason, "price": yes_price, "edge": 0.10}
            if rec == "bet_no":
                return {"action": "bet_no", "confidence": conf, "reason": reason, "price": no_price, "edge": 0.10}
            return {"action": "skip", "confidence": conf, "reason": reason, "price": yes_price}

    return None
