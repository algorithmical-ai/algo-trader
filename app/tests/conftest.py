import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

NY = pytz.timezone("America/New_York")


@pytest.fixture
def sample_1m_data():
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
    dates = pd.date_range("2024-01-01", periods=300, freq="B").tz_localize(NY)
    closes = np.linspace(100, 150, 300)  # clean uptrend
    df = pd.DataFrame(
        {
            "open": closes + np.random.randn(300),
            "high": closes + abs(np.random.randn(300)) * 2,
            "low": closes - abs(np.random.randn(300)) * 2,
            "close": closes,
            "volume": np.random.uniform(1e7, 1e8, 300),
        },
        index=dates,
    )
    return df


@pytest.fixture
def mock_redis():
    from unittest.mock import MagicMock

    mock = MagicMock()
    store = {}
    mock.hset.side_effect = lambda key, mapping=None, **kw: store.update(mapping or kw)
    mock.hgetall.side_effect = lambda key: (
        store.get(key.split(":")[1], {}) if ":" in key else {}
    )
    mock.delete.side_effect = lambda key: (
        store.pop(key.split(":")[1], None) if ":" in key else None
    )
    mock.keys.side_effect = lambda p: [f"position:{k}" for k in store.keys()]
    mock.expire.return_value = True
    return mock
