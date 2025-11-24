import pandas as pd
import numpy as np
import talib
from datetime import timedelta
from app.src.utils.helpers import now_ny, NY


def calculate_rvol(df_1m: pd.DataFrame) -> float:
    today = now_ny().date()
    today_vol = df_1m[df_1m.index.date == today]["volume"].sum()
    avg_vol_20d = df_1m["volume"].rolling(20 * 390).mean().iloc[-1]
    return today_vol / avg_vol_20d if avg_vol_20d > 0 else 0


def get_opening_range(df_today: pd.DataFrame, minutes: int = 15):
    market_open = df_today.index[0].replace(hour=9, minute=30, second=0, microsecond=0)
    orb_end = market_open + timedelta(minutes=minutes)
    orb_data = df_today[(df_today.index >= market_open) & (df_today.index <= orb_end)]
    if len(orb_data) == 0:
        return None, None
    return orb_data["high"].max(), orb_data["low"].min()


def calculate_vwap(df_today: pd.DataFrame):
    return (df_today["vwap"] * df_today["volume"]).sum() / df_today["volume"].sum()


def is_uptrend(daily_df: pd.DataFrame) -> bool:
    close = daily_df["close"]
    sma50 = talib.SMA(close.values, 50)
    sma200 = talib.SMA(close.values, 200)
    return close.iloc[-1] > sma50[-1] > sma200[-1] if len(sma200) > 0 else False


def is_downtrend(daily_df: pd.DataFrame) -> bool:
    close = daily_df["close"]
    sma50 = talib.SMA(close.values, 50)
    sma200 = talib.SMA(close.values, 200)
    return close.iloc[-1] < sma50[-1] < sma200[-1] if len(sma200) > 0 else False
