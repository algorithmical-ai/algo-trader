import redis.asyncio as redis
from src.config.settings import settings
from src.utils.logger import logger
import json
from typing import Dict, Any


class PositionStore:
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get_all(self) -> Dict[str, Any]:
        raw = await self.client.get("daytrader:positions")
        return json.loads(raw) if raw else {}

    async def save_all(self, positions: Dict[str, Any]):
        await self.client.set("daytrader:positions", json.dumps(positions))
        logger.debug(f"Persisted positions → {len(positions)} symbols")

    async def close(self):
        await self.client.close()
