from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest
import pytz

NY = pytz.timezone("America/New_York")


@pytest.fixture
def sample_1m_data():
    # 20 full trading days (7800 minutes) + today (390 minutes) = 8190 minutes total
    # Start exactly 20 trading days ago at 9:30 AM
    base = datetime(2025, 10, 27, 9, 30, tzinfo=NY)  # Monday
    index = []
    current = base
    for _ in range(21):  # 20 past + today
        for _ in range(390):  # 9:30 to 16:00 = 390 minutes
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
def mock_dynamodb(monkeypatch):

    # In-memory storage for tables
    open_positions = {}  # {(ticker, indicator): item}
    completed_trades = {}  # {(date, indicator): item}

    class MockTable:
        def __init__(self, table_name, store):
            self.table_name = table_name
            self.store = store

        def get_item(self, Key):
            key = (
                (Key["ticker"], Key["indicator"])
                if "ticker" in Key
                else (Key["date"], Key["indicator"])
            )
            if key in self.store:
                return {"Item": self.store[key].copy()}
            return {}

        def put_item(self, Item):
            if "ticker" in Item:
                key = (Item["ticker"], Item["indicator"])
            else:
                key = (Item["date"], Item["indicator"])
            self.store[key] = Item.copy()

        def delete_item(self, Key):
            key = (
                (Key["ticker"], Key["indicator"])
                if "ticker" in Key
                else (Key["date"], Key["indicator"])
            )
            if key in self.store:
                del self.store[key]

        def scan(
            self,
            FilterExpression=None,
            ExpressionAttributeValues=None,
            ExclusiveStartKey=None,
        ):
            items = []
            for key, item in self.store.items():
                # Simple filter matching for indicator
                if FilterExpression and ExpressionAttributeValues:
                    indicator_value = ExpressionAttributeValues.get(":ind")
                    if item.get("indicator") == indicator_value:
                        items.append(item.copy())
                else:
                    items.append(item.copy())

            response = {"Items": items}
            # No pagination in mock for simplicity
            return response

    class MockDynamoDBResource:
        def Table(self, table_name):
            if table_name == "AlgoTraderOpenPositions":
                return MockTable(table_name, open_positions)
            elif table_name == "CompletedTradesForAlgoTrader":
                return MockTable(table_name, completed_trades)
            return MockTable(table_name, {})

    mock_resource = MockDynamoDBResource()

    # Mock the _get_dynamodb_resource function
    def mock_get_dynamodb_resource():
        return mock_resource

    monkeypatch.setattr(
        "app.src.position_tracker.dynamodb_tracker._get_dynamodb_resource",
        mock_get_dynamodb_resource,
    )

    # Clear stores before each test
    open_positions.clear()
    completed_trades.clear()

    return {
        "resource": mock_resource,
        "open_positions": open_positions,
        "completed_trades": completed_trades,
    }
