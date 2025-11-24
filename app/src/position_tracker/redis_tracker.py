import json
import os
from redis import Redis
from loguru import logger

# Heroku Redis URL
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = Redis.from_url(redis_url, decode_responses=True)


class PositionTracker:
    @staticmethod
    def add_position(ticker: str, action: str, price: float, reason: str):
        key = f"position:{ticker}"
        data = {
            "action": action,  # buy_to_open or sell_to_open
            "entry_price": price,
            "reason": reason,
            "timestamp": json.dumps(None, default=str),  # for sorting
        }
        redis.hset(key, mapping=data)
        redis.expire(key, 60 * 60 * 24)  # 24h expiry
        logger.success(f"POSITION OPENED → {ticker} {action} @ ${price:.2f} | {reason}")

    @staticmethod
    def get_position(ticker: str):
        key = f"position:{ticker}"
        data = redis.hgetall(key)
        return data if data else None

    @staticmethod
    def close_position(ticker: str, exit_action: str, exit_price: float, reason: str):
        key = f"position:{ticker}"
        old = redis.hgetall(key)
        if old:
            pnl = (
                (exit_price - float(old["entry_price"]))
                / float(old["entry_price"])
                * 100
            )
            sign = "+" if "buy_to_open" in old["action"] else "-"
            redis.delete(key)
            logger.success(
                f"POSITION CLOSED → {ticker} {exit_action} @ ${exit_price:.2f} | PnL: {sign}{pnl:.2f}% | {reason}"
            )
        else:
            logger.warning(f"No position found to close: {ticker}")

    @staticmethod
    def get_all_open():
        keys = redis.keys("position:*")
        return [k.split(":")[1] for k in keys]
