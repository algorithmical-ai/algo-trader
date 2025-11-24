import pytest
import pandas as pd
import numpy as np
from algo_trader.indicators.technical import (
    calculate_rvol,
    get_opening_range,
    calculate_vwap,
    is_uptrend,
    is_downtrend,
)


def test_calculate_rvol(sample_1m_data):
    rvol = calculate_rvol(sample_1m_data)
    assert 0.5 <= rvol <= 2.0  # Reasonable range for random data


def test_get_opening_range(sample_1m_data):
    today_df = sample_1m_data[
        sample_1m_data.index.date == sample_1m_data.index[0].date()
    ]
    high, low = get_opening_range(today_df)
    assert high is not None and low is not None
    assert high >= today_df["high"].iloc[:15].max()
    assert low <= today_df["low"].iloc[:15].min()


def test_calculate_vwap(sample_1m_data):
    vwap = calculate_vwap(sample_1m_data)
    assert 99 <= vwap <= 106


def test_is_uptrend(sample_daily_data):
    assert is_uptrend(sample_daily_data)  # Our mock is upward drifting


def test_is_downtrend(sample_daily_data):
    down_df = sample_daily_data.copy()
    down_df["close"] = 200 - np.cumsum(np.random.randn(300).cumsum())
    assert is_downtrend(down_df)
