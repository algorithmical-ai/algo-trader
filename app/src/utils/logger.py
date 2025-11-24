from loguru import logger
import sys

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
)
logger.add(
    "logs/trading_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="10 days",
    level="DEBUG",
)
