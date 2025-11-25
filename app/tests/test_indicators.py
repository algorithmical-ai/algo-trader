from app.src.indicators.technical import (
    calculate_rvol,
    get_opening_range,
    calculate_vwap,
    is_uptrend,
    is_downtrend,
)
import numpy as np


def test_calculate_rvol(sample_1m_data):
    df = sample_1m_data.copy()
    today_mask = df.index.date == df.index[0].date()
    df.loc[today_mask, "volume"] = 7500.0  # exactly 1.5x
    rvol = calculate_rvol(df)
    assert 1.49 <= rvol <= 1.51  # tight tolerance


def test_get_opening_range(sample_1m_data):
    today_df = sample_1m_data[
        sample_1m_data.index.date == sample_1m_data.index[0].date()
    ]
    high, low = get_opening_range(today_df)
    assert high is not None and low is not None


def test_calculate_vwap(sample_1m_data):
    vwap = calculate_vwap(sample_1m_data)
    assert isinstance(vwap, float)


def test_is_uptrend(sample_daily_data):
    assert is_uptrend(sample_daily_data)


def test_is_downtrend(sample_daily_data):
    df = sample_daily_data.copy()
    df["close"] = np.linspace(200, 100, 300)
    assert is_downtrend(df)
