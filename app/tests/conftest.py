import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

NY = pytz.timezone("America/New_York")


@pytest.fixture
def sample_1m_data():
    # 20 full trading days (7800 minutes) + today (390 minutes) = 8190 minutes total
    # Start exactly 20 trading days ago at 9:30 AM
    base = datetime(2025, 10, 27, 9, 30, tzinfo=NY)  # Monday
    index = []
    current = base
    for day in range(21):  # 20 past + today
        for minute in range(390):  # 9:30 to 16:00 = 390 minutes
            if current.weekday() < 5:  # Mon-Fri only
                index.append(current)
            current += timedelta(minutes=1)
        current = current.replace(hour=9, minute=30) + timedelta(days=1)

    # Keep only valid trading minutes
    volume = np.full(len(index), 5000.0)
    volume[-390:] = 7500.0  # today = 1.5x

    df = pd.DataFrame(
        {
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": volume,
            "vwap": 100.5,
        },
        index=index[:8190],
    )  # exactly 20 full days + today
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


@pytest.fixture
def mock_redis(monkeypatch):
    from unittest.mock import MagicMock

    mock = MagicMock()
    store = {}
    mock.hset.side_effect = lambda key, mapping: store.update(mapping)
    mock.hgetall.side_effect = lambda key: store if "AAPL" in key else {}
    mock.delete.side_effect = lambda key: store.clear() if "AAPL" in key else None
    monkeypatch.setattr("app.src.position_tracker.redis_tracker.redis_client", mock)
    return mock
