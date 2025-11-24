from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from app.src.config.settings import settings

client = StockHistoricalDataClient(settings.ALPACA_KEY, settings.ALPACA_SECRET)


async def get_bars(symbols, timeframe=TimeFrame.Minute, limit=1000):
    request = StockBarsRequest(
        symbol_or_symbols=symbols, timeframe=timeframe, limit=limit, adjustment="all"
    )
    return client.get_stock_bars(request).df
