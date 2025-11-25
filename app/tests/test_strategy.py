import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.src.strategies.orb_vwap_uw import evaluate_ticker
from app.src.core.signaler import send_signal
from app.src.position_tracker.redis_tracker import PositionTracker


@pytest.mark.asyncio
async def test_orb_long_entry(sample_1m_data, sample_daily_data, mocker):
    session = MagicMock()
    mocker.patch(
        "app.src.strategies.orb_vwap_uw.now_ny",
        return_value=sample_1m_data.index[20],
    )
    mocker.patch(
        "app.src.strategies.orb_vwap_uw.get_flow_signal", return_value="bullish"
    )
    mocker.patch(
        "app.src.position_tracker.redis_tracker.redis_client", new=MagicMock()
    )

    # Force price above ORB high and VWAP
    today_df = sample_1m_data[
        sample_1m_data.index.date == sample_1m_data.index[0].date()
    ]
    orb_high, _ = today_df.iloc[:15]["high"].max(), today_df.iloc[:15]["low"].min()
    sample_1m_data.loc[sample_1m_data.index[30:], "close"] = orb_high + 5

    await evaluate_ticker("TEST", sample_1m_data, sample_daily_data, session)
    # Should trigger long
    assert PositionTracker.get_position("TEST") is not None
    assert PositionTracker.get_position("TEST")["action"] == "buy_to_open"


@pytest.mark.asyncio
async def test_exit_on_profit(sample_1m_data, sample_daily_data, mocker):
    session = AsyncMock()
    mocker.patch(
        "app.src.strategies.orb_vwap_uw.now_ny",
        return_value=sample_1m_data.index[-1],
    )
    mocker.patch("app.src.position_tracker.redis_tracker.redis_client")

    # Simulate open long at 100, current 105 → +5%
    from app.src.position_tracker.redis_tracker import redis_client

    redis_client.hset(
        "position:TEST",
        mapping={"action": "buy_to_open", "entry_price": "100.0", "reason": "test"},
    )

    sample_1m_data["close"].iloc[-1] = 105.0

    await evaluate_ticker("TEST", sample_1m_data, sample_daily_data, session)

    # Should close
    assert redis_client.delete.called
    session.post.assert_called()
