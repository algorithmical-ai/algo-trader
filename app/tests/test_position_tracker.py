from algo_trader.position_tracker.redis_tracker import PositionTracker


def test_position_lifecycle(mock_redis):
    from algo_trader.position_tracker.redis_tracker import redis_client

    redis_client = mock_redis

    PositionTracker.add_position("AAPL", "buy_to_open", 150.0, "test entry")
    pos = PositionTracker.get_position("AAPL")
    assert pos["action"] == "buy_to_open"
    assert float(pos["entry_price"]) == 150.0

    PositionTracker.close_position("AAPL", "sell_to_close", 160.0, "profit")
    assert PositionTracker.get_position("AAPL") is None
