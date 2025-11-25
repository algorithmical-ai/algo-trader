import json
import os
from datetime import datetime

from redis import Redis

from app.src.config.settings import settings
from app.src.utils.logger import logger

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


class PositionTracker:
    @staticmethod
    def add_position(ticker: str, action: str, price: float, reason: str):
        key = f"position:{ticker}"
        data = {
            "action": action,
            "entry_price": str(price),
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
        redis_client.hset(key, mapping=data)
        redis_client.expire(key, 86400)  # 24 hours
        logger.info(f"POSITION ADDED: {ticker} {action} @ ${price:.2f} | {reason}")

    @staticmethod
    def get_position(ticker: str) -> dict | None:
        key = f"position:{ticker}"
        data = redis_client.hgetall(key)
        if data:
            data["entry_price"] = float(data["entry_price"])
            return data
        return None

    @staticmethod
    def close_position(ticker: str, exit_action: str, exit_price: float, reason: str):
        key = f"position:{ticker}"
        pos = redis_client.hgetall(key)
        if pos:
            entry_price = float(pos["entry_price"])
            pnl_pct = (
                ((exit_price - entry_price) / entry_price) * 100
                if "buy_to_open" in pos["action"]
                else ((entry_price - exit_price) / entry_price) * 100
            )
            redis_client.delete(key)
            logger.info(
                f"POSITION CLOSED: {ticker} {exit_action} @ ${exit_price:.2f} | PnL: {pnl_pct:+.2f}% | {reason}"
            )
        else:
            logger.info(f"No open position for {ticker}")

    @staticmethod
    def get_open_positions() -> list[str]:
        keys = redis_client.keys("position:*")
        return [k.decode().split(":")[1] for k in keys]
