import asyncio
from src.core.trader import DayTrader
from src.utils.logger import logger


async def main():
    trader = DayTrader()
    await trader.start()


if __name__ == "__main__":
    logger.success("DayTrader-Pro booting up...")
    asyncio.run(main())
