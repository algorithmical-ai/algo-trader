import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

NY = pytz.timezone("America/New_York")


@pytest.fixture
def sample_1m_data():
    base = datetime(2025, 11, 24, 9, 30, tzinfo=NY)
    index = [base + timedelta(minutes=i) for i in range(1000)]
    df = pd.DataFrame(
        {
            "open": 100 + np.cumsum(np.random.randn(1000) * 0.1),
            "high": 101 + np.cumsum(np.random.randn(1000) * 0.1),
            "low": 99 + np.cumsum(np.random.randn(1000) * 0.1),
            "close": 100 + np.cumsum(np.random.randn(1000) * 0.1),
            "volume": np.full(1000, 5000.0),  # deterministic
            "vwap": 100.5,
        },
        index=index,
    )
    df.index.name = "timestamp"
    return df


@pytest.fixture
def sample_daily_data():
    dates = pd.date_range("2024-01-01", periods=300, freq="B").tz_localize(NY)
    closes = np.linspace(100, 200, 300)
    df = pd.DataFrame(
        {
            "open": closes * 0.99,
            "high": closes * 1.01,
            "low": closes * 0.98,
            "close": closes,
            "volume": 1e7,
        },
        index=dates,
    )
    return df
