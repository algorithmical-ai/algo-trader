from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from src.data.tickers import TOP_2025_TICKERS
from src.core.signals import generate_signal
from src.persistence.redis_store import PositionStore
from src.webhook.sender import send_signal
from src.utils.logger import logger
import asyncio


class DayTrader:
    def __init__(self):
        self.data_client = StockHistoricalDataClient()
        self.store = PositionStore()
        self.last_signals = {}  # simple in-memory dedupe

    async def run_once(self):
        positions = await self.store.get_all()
        end = datetime.utcnow()
        start = end - timedelta(days=30)

        request_params = StockBarsRequest(
            symbol_or_symbols=TOP_2025_TICKERS,
            timeframe=TimeFrame.Hour,
            start=start,
            end=end,
            adjustment="all",
        )

        bars = self.data_client.get_stock_bars(request_params).df
        if bars.empty:
            logger.warning("No bars received")
            return

        for symbol in TOP_2025_TICKERS:
            try:
                if symbol not in bars.index.get_level_values(0):
                    continue
                df = bars.xs(symbol, level=0)
                df = df.tail(100)

                signal = generate_signal(symbol, df)
                if signal and signal["timestamp"] not in self.last_signals.get(
                    symbol, []
                ):
                    await send_signal(signal)

                    # Track to avoid duplicates in same run
                    self.last_signals.setdefault(symbol, []).append(signal["timestamp"])

                    # Persist fake position for future reference (survives dyno restart)
                    positions[symbol] = positions.get(symbol, 0) + (
                        1 if signal["side"] == "buy" else -1
                    )
                    logger.info(f"Position updated {symbol}: {positions[symbol]}")

            except Exception as e:
                logger.exception(f"Error processing {symbol}: {e}")

        await self.store.save_all(positions)

    async def start(self):
        logger.success("DayTrader-Pro 2025 started – signal-only mode")
        while True:
            try:
                await self.run_once()
                logger.info("Cycle complete – sleeping 1 hour")
                await asyncio.sleep(3600)
            # every hour on Heroku free dyno wake-up
            except Exception as e:
                logger.exception(f"Critical error: {e}")
                await asyncio.sleep(60)
