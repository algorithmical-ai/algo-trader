import numpy as np
import pandas as pd
from app.src.indicators.technical import calculate_rvol, get_opening_range, calculate_vwap, is_uptrend, is_downtrend

def test_calculate_rvol(sample_1m_data):
    # Force realistic volume: today = 1.5x average
    df = sample_1m_data.copy()
    today_start = df.index[0].date()
    today_mask = df.index.date == today_start
    df.loc[today_mask, 'volume'] *= 1.5
    rvol = calculate_rvol(df)
    assert 1.0 <= rvol <= 3.0

def test_get_opening_range(sample_1m_data):
    today_df = sample_1m_data[sample_1m_data.index.date == sample_1m_data.index[0].date()]
    high, low = get_opening_range(today_df)
    assert high >= today_df['high'].iloc[:15].max()
    assert low <= today_df['low'].iloc[:15].min()

def test_calculate_vwap(sample_1m_data):
    vwap = calculate_vwap(sample_1m_data)
    assert isinstance(vwap, float)

def test_is_uptrend(sample_daily_data):
    df = sample_daily_data.copy()
    df['close'] = np.linspace(100, 150, len(df))  # strong uptrend
    assert is_uptrend(df)

def test_is_downtrend(sample_daily_data):
    df = sample_daily_data.copy()
    df['close'] = np.linspace(150, 100, len(df))  # strong downtrend
    assert is_downtrend(df)
