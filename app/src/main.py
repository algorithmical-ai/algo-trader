import asyncio

import aiohttp

from app.src.core.scanner import scan_once
from app.src.strategies.orb_vwap_uw import refresh_watchlist
from app.src.utils.helpers import now_ny
from app.src.utils.logger import logger


async def main():
    logger.success(
        f"[{now_ny()}] Grok Elite 2025 Bot Started | Max UW Flow + Congress + Dark Pool"
    )
    async with aiohttp.ClientSession() as session:
        await refresh_watchlist(session)  # New: Daily screener refresh
        while True:
            try:
                await scan_once(session)
                await asyncio.sleep(25)
            except Exception as e:
                logger.critical(f"Main loop error: {e}")
                await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
