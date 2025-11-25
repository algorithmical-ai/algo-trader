import asyncio
from datetime import time

import aiohttp

from app.src.core.scanner import scan_once
from app.src.strategies.orb_vwap_uw import refresh_watchlist
from app.src.utils.helpers import now_ny
from app.src.utils.logger import logger
from app.src.strategies.wheel_master import run_weekly_put_wheel

async def main():
    logger.success(
        f"[{now_ny()}] Algo Trader 2025 Bot Started | Max UW Flow + Congress + Dark Pool"
    )
    async with aiohttp.ClientSession() as session:
        # Track last refresh date to ensure daily refresh at 9:30 AM ET
        last_refresh_date = None

        while True:
            try:
                # Check if it's time to refresh watchlist (9:30 AM ET daily)
                now = now_ny()
                current_date = now.date()
                current_time = now.time()
                refresh_time_start = time(hour=9, minute=29)
                refresh_time_end = time(hour=9, minute=31)

                # Refresh if it's between 9:29-9:31 AM ET and we haven't refreshed today
                if (
                    refresh_time_start <= current_time <= refresh_time_end
                    and last_refresh_date != current_date
                ):
                    logger.info("Refreshing watchlist at 9:30 AM ET")
                    await refresh_watchlist(session)
                    last_refresh_date = current_date
                    await asyncio.sleep(60)  # Prevent double refresh

                await scan_once(session)
                await run_weekly_put_wheel(session)
                await asyncio.sleep(25)
            except Exception as e:
                logger.critical(f"Main loop error: {e}")
                await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
