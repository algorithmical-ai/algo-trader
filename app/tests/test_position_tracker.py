from app.src.position_tracker.dynamodb_tracker import PositionTracker


def test_position_lifecycle(mock_dynamodb):
    """Test the full lifecycle of adding, getting, and closing a position."""
    # The mock_dynamodb fixture is needed to set up the DynamoDB mocks
    _ = mock_dynamodb  # Explicitly mark as used for linter

    PositionTracker.add_position("AAPL", "buy_to_open", 150.0, "test")
    pos = PositionTracker.get_position("AAPL")
    assert pos is not None
    assert pos["action"] == "buy_to_open"
    assert pos["entry_price"] == 150.0
    PositionTracker.close_position("AAPL", "sell_to_close", 160.0, "profit")
    pos_after_close = PositionTracker.get_position("AAPL")
    assert pos_after_close is None
