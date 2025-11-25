from unittest.mock import MagicMock

import pytest

from app.src.core.signaler import send_signal


@pytest.mark.asyncio
async def test_signal_payload():
    session = MagicMock()
    response = MagicMock(status=200)
    session.post.return_value.__aenter__.return_value = response

    await send_signal("NVDA", "buy_to_open", "test", 850.0, session)  # type: ignore
    payload = session.post.call_args[1]["json"]
    assert payload["ticker_symbol"] == "NVDA"
    assert payload["price"] == "850.0"
