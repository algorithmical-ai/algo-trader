import pytest
from algo_trader.core.signaler import send_signal


@pytest.mark.asyncio
async def test_signal_payload():
    session = MagicMock()
    response = MagicMock()
    response.status = 200
    session.post.return_value.__aenter__.return_value = response

    await send_signal("NVDA", "buy_to_open", "ORB Breakout", 850.0, session)

    session.post.assert_called_once()
    args, kwargs = session.post.call_args
    payload = kwargs["json"]
    assert payload["ticker_symbol"] == "NVDA"
    assert payload["action"] == "buy_to_open"
    assert "reason" in payload
    assert payload["price"] == 850.0
