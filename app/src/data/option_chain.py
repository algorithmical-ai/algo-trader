from datetime import datetime, timedelta

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest

from app.src.config.settings import settings
from app.src.utils.logger import logger

trading_client = TradingClient(settings.ALPACA_KEY, settings.ALPACA_SECRET, paper=False)


async def get_option_chain(
    ticker: str, option_type: str = "put", days: int = 45
) -> list:
    """Fetch real option chain from Alpaca for puts/calls."""
    try:
        request = GetOptionContractsRequest(
            underlying_symbols=[ticker], limit=100  # Top 100 strikes
        )
        contracts = trading_client.get_option_contracts(request)

        chain = []
        for c in contracts:
            # c is likely a tuple or dict, not an object; try handling both cases.
            # Try to support both tuple (with keys as field names) and dict access.
            # We'll attempt to support tuple[str, Any], dict, or similar container.
            expiration_date = None
            symbol = None
            strike_price = None
            # Try to retrieve expiration_date: support dict, tuple/list, or attribute
            if isinstance(c, dict) and "expiration_date" in c:
                expiration_date = c["expiration_date"]
            elif isinstance(c, (tuple, list)) and len(c) >= 3:
                # Assumed ordering: [symbol, strike_price, expiration_date, ...]
                expiration_date = c[2]
            else:
                # Try to get expiration_date as an attribute (for object types)
                expiration_date = getattr(c, "expiration_date", None)

            # Now parse the expiration_date as string if needed
            if expiration_date:
                # Convert both sides to datetime before comparing.
                try:
                    expiration_dt = datetime.fromisoformat(str(expiration_date))
                except Exception:
                    continue
                cutoff_dt = datetime.now() + timedelta(days=days)
                if expiration_dt > cutoff_dt:
                    # Now get symbol and strike_price
                    if isinstance(c, dict) and "symbol" in c:
                        symbol = c["symbol"]
                    elif isinstance(c, (tuple, list)) and len(c) >= 1:
                        symbol = c[0]
                    if isinstance(c, dict) and "strike_price" in c:
                        strike_price = c["strike_price"]
                    elif isinstance(c, (tuple, list)) and len(c) >= 2:
                        strike_price = c[1]
                    chain.append(
                        {
                            "symbol": symbol,
                            "strike_price": strike_price,
                            "expiration_date": expiration_date,
                            "option_type": option_type,
                        }
                    )
        logger.info(
            f"Option chain for {ticker} ({option_type}): {len(chain)} contracts"
        )
        return chain
    except Exception as e:
        logger.error(f"Option chain error for {ticker}: {e}")
        return []
