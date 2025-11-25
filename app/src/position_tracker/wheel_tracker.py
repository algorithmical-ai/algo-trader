import json
from datetime import datetime

from redis import Redis

from app.src.config.settings import settings
from app.src.utils.logger import logger

# Connect to Heroku Redis (or local)
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


class WheelTracker:
    @staticmethod
    def _key(ticker: str, type_: str = "put") -> str:
        return f"wheel:{type_}:{ticker}"

    @staticmethod
    def record_put_sold(ticker: str, put_data: dict):
        """Save sold put to Redis (persists forever)"""
        key = WheelTracker._key(ticker, "put")
        data = {**put_data, "sold_at": datetime.utcnow().isoformat(), "ticker": ticker}
        redis_client.hset(key, mapping=data)
        redis_client.expire(key, 60 * 60 * 24 * 90)  # 90 days
        logger.success(
            f"WHEEL PUT SOLD → {ticker} {put_data['strike']} | Credit ${put_data['premium']:.2f}"
        )

    @staticmethod
    def record_call_sold(ticker: str, call_data: dict):
        """Save sold covered call"""
        key = WheelTracker._key(ticker, "call")
        data = {**call_data, "sold_at": datetime.utcnow().isoformat(), "ticker": ticker}
        redis_client.hset(key, mapping=data)
        redis_client.expire(key, 60 * 60 * 24 * 90)
        logger.success(f"WHEEL CALL SOLD → {ticker} {call_data['strike']}")

    @staticmethod
    def record_assignment(ticker: str):
        """Remove put when assigned"""
        key = WheelTracker._key(ticker, "put")
        if redis_client.exists(key):
            redis_client.delete(key)
            logger.warning(f"WHEEL ASSIGNMENT → {ticker} (put removed)")

    @staticmethod
    def get_open_puts() -> dict:
        """Return all active sold puts"""
        keys = redis_client.keys("wheel:put:*")
        puts = {}
        for key in keys:
            ticker = key.split(":")[-1]
            data = redis_client.hgetall(key)
            if data:
                puts[ticker] = data
        return puts

    @staticmethod
    def get_open_calls() -> dict:
        """Return all active covered calls"""
        keys = redis_client.keys("wheel:call:*")
        calls = {}
        for key in keys:
            ticker = key.split(":")[-1]
            data = redis_client.hgetall(key)
            if data:
                calls[ticker] = data
        return calls

    @staticmethod
    def clear_all():
        """Emergency cleanup (use carefully)"""
        redis_client.delete(*redis_client.keys("wheel:*"))
        logger.info("WHEEL TRACKER: All records cleared")
