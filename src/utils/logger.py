"""Basic logging setup using loguru."""

import sys
from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """Configure loguru: level, format, and stderr handler."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level,
    )
