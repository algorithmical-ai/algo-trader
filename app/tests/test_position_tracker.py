from unittest.mock import MagicMock
from app.src.position_tracker.redis_tracker import PositionTracker, redis_client


def test_position_lifecycle(monkeypatch):
    mock = MagicMock()
    store = {}
    mock.hset.side_effect = lambda key, mapping: store.update(mapping)
    mock.hgetall.side_effect = lambda key: store if "AAPL" in key else {}
    mock.delete.side_effect = lambda key: store.clear()
    monkeypatch.setattr("app.src.position_tracker.redis_tracker.redis_client", mock)

    PositionTracker.add_position("AAPL", "buy_to_open", 150.0, "test")
    pos = PositionTracker.get_position("AAPL")
    assert pos["action"] == "buy_to_open"

    PositionTracker.close_position("AAPL", "sell_to_close", 160.0, "profit")
    assert PositionTracker.get_position("AAPL") is None
