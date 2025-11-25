from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

import pandas as pd  # type: ignore[import-untyped]
from alpaca.data import StockBarsRequest, StockHistoricalDataClient, TimeFrame

from app.src.config.settings import settings
from app.src.utils.logger import logger

client = StockHistoricalDataClient(settings.ALPACA_KEY, settings.ALPACA_SECRET)


def _chunk_symbols(symbols: list[str], chunk_size: int) -> Iterable[list[str]]:
    for idx in range(0, len(symbols), chunk_size):
        yield symbols[idx : idx + chunk_size]


def _is_daily_timeframe(timeframe) -> bool:
    if isinstance(timeframe, TimeFrame):
        # TimeFrame objects have a string value like '1Min' or '1Day'
        timeframe_str = str(timeframe).lower()
        return "day" in timeframe_str
    if isinstance(timeframe, str):
        normalized = timeframe.strip().lower()
        return normalized in {"1day", "day", "1d"}
    return False


def _default_start(timeframe: TimeFrame | str) -> datetime | None:
    if _is_daily_timeframe(timeframe):
        return (datetime.now(timezone.utc) - timedelta(days=400)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    return None


async def get_bars(
    symbols,
    timeframe=TimeFrame.Minute,
    limit=1000,
    chunk_size: int = 20,
    start: datetime | None = None,
):
    if not symbols:
        logger.warning("get_bars called with no symbols")
        return None

    if isinstance(symbols, str):
        symbols = [symbols]

    if start is None:
        start = _default_start(timeframe)

    frames: list[pd.DataFrame] = []
    for chunk in _chunk_symbols(symbols, chunk_size):
        try:
            request_kwargs = dict(
                symbol_or_symbols=chunk,
                timeframe=timeframe,
                limit=limit,
                adjustment="all",
            )
            if start is not None:
                request_kwargs["start"] = start.isoformat()

            request = StockBarsRequest(**request_kwargs)
            bars = client.get_stock_bars(request)
            df = getattr(bars, "df", None)
            if df is not None and not df.empty:
                frames.append(df)
            else:
                logger.warning(
                    f"Alpaca returned no data for chunk {chunk} ({timeframe})"
                )
        except Exception as e:
            logger.error(f"Alpaca bars error for chunk {chunk}: {e}")

    if not frames:
        logger.error("Alpaca bars fetch produced no data across all chunks")
        return None

    combined = pd.concat(frames).sort_index()
    return combined
