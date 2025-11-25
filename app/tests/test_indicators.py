from app.src.indicators.technical import (
    calculate_rvol,
    get_opening_range,
    calculate_vwap,
    is_uptrend,
    is_downtrend,
)
import numpy as np
from unittest.mock import patch
from datetime import datetime
import pytz

NY = pytz.timezone("America/New_York")


def test_calculate_rvol(sample_1m_data):
    df = sample_1m_data.copy()
    today_mask = df.index.date == df.index[-1].date()
    df.loc[today_mask, "volume"] = 7500.0

    # Mock now_ny() to return the last date in the test data
    last_date = df.index[-1].date()
    mock_now = datetime.combine(last_date, datetime.min.time()).replace(tzinfo=NY)

    with patch("app.src.indicators.technical.now_ny", return_value=mock_now):
        rvol = calculate_rvol(df)
    assert 1.49 <= rvol <= 1.51


def test_get_opening_range(sample_1m_data):
    # Get the last date (today) from the test data
    today_df = sample_1m_data[
        sample_1m_data.index.date == sample_1m_data.index[-1].date()
    ]
    high, low = get_opening_range(today_df)
    assert high is not None
    assert low is not None


def test_calculate_vwap(sample_1m_data):
    assert abs(calculate_vwap(sample_1m_data) - 100.5) < 0.1


def test_is_uptrend(sample_daily_data):
    assert is_uptrend(sample_daily_data)


def test_is_downtrend(sample_daily_data):
    df = sample_daily_data.copy()
    df["close"] = np.linspace(200, 100, 300)
    assert is_downtrend(df)
