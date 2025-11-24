import pandas as pd
import numpy as np
import talib
from datetime import timedelta
from ..utils.helpers import now_ny, NY
from ..config.settings import settings
from ..logger import logger


def calculate_rvol(df_1m: pd.DataFrame) -> float:
    if len(df_1m) < 100:
        return 0.0
    today = now_ny().date()
    today_vol = df_1m[df_1m.index.date == today]["volume"].sum()
    avg_vol = df_1m["volume"].rolling(window=20 * 390, min_periods=10).mean().iloc[-1]
    return today_vol / avg_vol if avg_vol > 0 else 0.0


def get_opening_range(df_today: pd.DataFrame) -> tuple[float, float]:
    market_open = df_today.index[0].replace(
        hour=9, minute=30, second=0, microsecond=0, tzinfo=NY
    )
    orb_end = market_open + timedelta(minutes=settings.ORB_MINUTES)
    orb_data = df_today[(df_today.index >= market_open) & (df_today.index <= orb_end)]
    if len(orb_data) == 0:
        return None, None
    return orb_data["high"].max(), orb_data["low"].min()


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
