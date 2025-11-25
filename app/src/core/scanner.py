import asyncio

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import TimeFrame

from app.src.config.settings import settings
from app.src.data.alpaca_client import get_bars
from app.src.strategies.orb_vwap_uw import evaluate_ticker
from app.src.utils.helpers import is_trading_hours
from app.src.utils.logger import logger

trading_client = TradingClient(settings.ALPACA_KEY, settings.ALPACA_SECRET, paper=True)


async def scan_once(session):
    clock = trading_client.get_clock()
    if not clock.is_open or not is_trading_hours():
        logger.info("Skipping scan: Market closed or outside hours")
        return

    logger.info(f"Scanning {len(settings.WATCHLIST)} tickers...")
    df_1m = await get_bars(settings.WATCHLIST, TimeFrame.Minute, 1000)
    df_daily = await get_bars(settings.WATCHLIST, TimeFrame.Day, 300)

    if df_1m is None or df_daily is None:
        logger.warning("Failed to fetch bars, skipping scan")
        return

    tasks = [
        evaluate_ticker(ticker, df_1m, df_daily, session)
        for ticker in settings.WATCHLIST
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Scan complete")
