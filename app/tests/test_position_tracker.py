from app.src.position_tracker.redis_tracker import PositionTracker


def test_position_lifecycle(mock_redis):  # noqa: W0613
    PositionTracker.add_position("AAPL", "buy_to_open", 150.0, "test")
    pos = PositionTracker.get_position("AAPL")
    assert pos["action"] == "buy_to_open"
    PositionTracker.close_position("AAPL", "sell_to_close", 160.0, "profit")
    assert PositionTracker.get_position("AAPL") is None
