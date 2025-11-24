import asyncio
import aiohttp
from core.scanner import scan_once
from logger import logger
from utils.helpers import now_ny


async def main():
    logger.success(
        f"[{now_ny()}] Algo Trader Elite Bot Started - 100 Tickers | Redis | Webhooks"
    )
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        while True:
            try:
                await scan_once(session)
                await asyncio.sleep(25)  # Scan every 25s during market hours
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.critical(f"Main loop error: {e}")
                await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
