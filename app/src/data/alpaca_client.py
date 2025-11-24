from alpaca.data import StockHistoricalDataClient, StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from ..config.settings import settings
from ..logger import logger

client = StockHistoricalDataClient(settings.ALPACA_KEY, settings.ALPACA_SECRET)


async def get_bars(symbols, timeframe=TimeFrame.Minute, limit=1000):
    try:
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=timeframe,
            limit=limit,
            adjustment="all",
        )
        bars = client.get_stock_bars(request)
        return bars.df
    except Exception as e:
        logger.error(f"Alpaca bars error: {e}")
        return None
