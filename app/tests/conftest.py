import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from unittest.mock import MagicMock

NY = pytz.timezone("America/New_York")


@pytest.fixture
def sample_1m_data():
    """1000 minutes of 1-min bars (today + previous days)"""
    base_time = datetime(2025, 11, 24, 9, 30, tzinfo=NY)
    index = [base_time + timedelta(minutes=i) for i in range(1000)]
    df = pd.DataFrame(
        {
            "open": np.random.uniform(100, 105, 1000),
            "high": np.random.uniform(101, 106, 1000),
            "low": np.random.uniform(99, 104, 1000),
            "close": np.random.uniform(100, 105, 1000),
            "volume": np.random.uniform(1000, 10000, 1000),
            "vwap": np.random.uniform(100, 105, 1000),
        },
        index=index,
    )
    df.index.name = "timestamp"
    return df


@pytest.fixture
def sample_daily_data():
    dates = pd.date_range("2024-01-01", periods=300, freq="B")  # business days
    closes = np.cumsum(np.random.randn(300) * 2) + 100
    df = pd.DataFrame(
        {
            "open": closes + np.random.randn(300),
            "high": closes + abs(np.random.randn(300)) * 2,
            "low": closes - abs(np.random.randn(300)) * 2,
            "close": closes,
            "volume": np.random.uniform(1e7, 1e8, 300),
        },
        index=dates.tz_localize(NY),
    )
    return df


@pytest.fixture
def mock_redis():
    from redis import Redis

    mock = MagicMock(spec=Redis)
    store = {}  # Simulate Redis hash storage

    def hset(key, mapping=None, **kwargs):
        store[key] = mapping or kwargs

    def hgetall(key):
        return store.get(key, {})

    def delete(key):
        store.pop(key, None)

    def keys(pattern):
        return [k for k in store.keys() if pattern in k]

    mock.hset.side_effect = hset
    mock.hgetall.side_effect = hgetall
    mock.delete.side_effect = delete
    mock.keys.side_effect = keys
    mock.expire.return_value = True
    return mock
