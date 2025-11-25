from datetime import datetime, time, timedelta

import pandas as pd
import talib

from app.src.config.settings import settings
from app.src.utils.helpers import NY, now_ny
from app.src.utils.logger import logger


def calculate_rvol(df_1m: pd.DataFrame) -> float:
    if len(df_1m) < 100:
        return 0.0
    today = now_ny().date()
    today_mask = df_1m.index.date == today
    today_vol = df_1m[today_mask]["volume"].sum()

    # Calculate average volume per minute over the last 20 trading days, excluding today
    historical_df = df_1m[~today_mask]
    if len(historical_df) < 10:
        return 0.0
    avg_vol_per_min = (
        historical_df["volume"].rolling(window=20 * 390, min_periods=10).mean().iloc[-1]
    )
    # Convert to average daily volume (390 minutes per trading day)
    avg_daily_vol = avg_vol_per_min * 390
    return today_vol / avg_daily_vol if avg_daily_vol > 0 else 0.0


def get_opening_range(df_today: pd.DataFrame) -> tuple[float, float]:
    if len(df_today) == 0:
        return None, None  # type: ignore

    # Get the date from the first index and create market open time
    first_date = df_today.index[0].date()
    market_open_naive = datetime.combine(first_date, time(9, 30))

    # Make timezone-aware in NY timezone
    if market_open_naive.tzinfo is None:
        market_open = NY.localize(market_open_naive)
    else:
        market_open = market_open_naive.astimezone(NY)

    orb_end = market_open + timedelta(minutes=settings.ORB_MINUTES)
    orb_data = df_today[(df_today.index >= market_open) & (df_today.index <= orb_end)]
    if len(orb_data) == 0:
        return None, None  # type: ignore
    return orb_data["high"].max(), orb_data["low"].min()  # type: ignore


def calculate_vwap(df_today: pd.DataFrame) -> float:
    if df_today["volume"].sum() == 0:
        return df_today["close"].iloc[-1]
    return (df_today["close"] * df_today["volume"]).sum() / df_today["volume"].sum()


def is_uptrend(daily_df: pd.DataFrame) -> bool:
    if len(daily_df) < 200:
        return False
    close = daily_df["close"].values
    sma50 = talib.SMA(close, timeperiod=50)
    sma200 = talib.SMA(close, timeperiod=200)
    return close[-1] > sma50[-1] > sma200[-1]


def is_downtrend(daily_df: pd.DataFrame) -> bool:
    if len(daily_df) < 200:
        return False
    close = daily_df["close"].values
    sma50 = talib.SMA(close, timeperiod=50)
    sma200 = talib.SMA(close, timeperiod=200)
    return close[-1] < sma50[-1] < sma200[-1]
