import asyncio

from alpaca.data import TimeFrame
from alpaca.trading.client import TradingClient

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

    symbols = [ticker for ticker in settings.WATCHLIST if ticker not in settings.BLOCKED_TICKERS]
    if not symbols:
        logger.warning("No symbols available to scan after applying block list")
        return

    logger.info(f"Scanning {len(symbols)} tickers...")
    df_1m = await get_bars(symbols, TimeFrame.Minute, 1000, chunk_size=1)
    df_daily = await get_bars(symbols, TimeFrame.Day, 300, chunk_size=1)

    if df_1m is None or df_daily is None:
        logger.warning("Failed to fetch bars, skipping scan")
        return

    idx_1m = df_1m.index.get_level_values(0)
    idx_daily = df_daily.index.get_level_values(0)
    missing_intraday = [ticker for ticker in symbols if ticker not in idx_1m]
    missing_daily = [ticker for ticker in symbols if ticker not in idx_daily]

    if missing_intraday:
        logger.warning(f"Intraday data missing for: {', '.join(missing_intraday)}")
    if missing_daily:
        logger.warning(f"Daily data missing for: {', '.join(missing_daily)}")

    active_symbols = [
        ticker
        for ticker in symbols
        if ticker not in missing_intraday and ticker not in missing_daily
    ]

    if not active_symbols:
        logger.warning("No symbols have both intraday and daily data; skipping scan")
        return

    tasks = [evaluate_ticker(ticker, df_1m, df_daily, session) for ticker in active_symbols]
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Scan complete")
