"""Central logging setup using loguru."""

import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")


def get_logger():
    """Return the configured logger for use across the app."""
    return logger
