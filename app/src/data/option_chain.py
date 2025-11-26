import re
from datetime import datetime, timedelta
from typing import Optional

import aiohttp

from app.src.config.settings import settings
from app.src.utils.logger import logger


def _parse_contract_symbol(contract_symbol: str) -> Optional[dict]:
    """
    Parse Alpaca option contract symbol format: AAPL261218P00005000
    Format: {UNDERLYING}{YYMMDD}{P|C}{STRIKE_IN_CENTS}
    Returns dict with underlying, expiration_date, option_type, strike_price
    """
    # Pattern: underlying (1-5 chars) + date (6 digits YYMMDD) + type (P or C) + strike (8 digits)
    pattern = r"^([A-Z]{1,5})(\d{6})([PC])(\d{8})$"
    match = re.match(pattern, contract_symbol)
    if not match:
        return None
    
    underlying, date_str, opt_type, strike_str = match.groups()
    
    # Parse date: YYMMDD -> YYYY-MM-DD
    year = 2000 + int(date_str[:2])
    month = int(date_str[2:4])
    day = int(date_str[4:6])
    try:
        expiration_date = datetime(year, month, day)
    except ValueError:
        return None
    
    # Parse strike: 00005000 -> 50.00
    strike_price = float(strike_str) / 1000.0
    
    # Map P/C to put/call
    option_type = "put" if opt_type == "P" else "call"
    
    return {
        "underlying": underlying,
        "expiration_date": expiration_date.isoformat(),
        "option_type": option_type,
        "strike_price": strike_price,
    }


async def get_option_chain(
    ticker: str, option_type: str = "put", days: int = 45, session: Optional[aiohttp.ClientSession] = None
) -> list:
    """
    Fetch real option chain from Alpaca REST API for puts/calls.
    Uses /v1beta1/options/snapshots endpoint and parses contract symbols.
    """
    try:
        # Calculate expiration date filter (today + days)
        expiration_date_gte = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        expiration_date_lte = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Map option_type to API format
        api_type = "put" if option_type.lower() == "put" else "call"
        
        url = f"https://data.alpaca.markets/v1beta1/options/snapshots/{ticker}"
        if not settings.ALPACA_KEY or not settings.ALPACA_SECRET:
            logger.error("Alpaca credentials not configured")
            return []
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": str(settings.ALPACA_KEY),
            "APCA-API-SECRET-KEY": str(settings.ALPACA_SECRET),
        }
        params = {
            "feed": "opra",
            "type": api_type,
            "expiration_date_gte": expiration_date_gte,
            "expiration_date_lte": expiration_date_lte,
            "limit": "100",
        }
        
        # Use provided session or create a temporary one
        timeout = aiohttp.ClientTimeout(total=10)
        if session is None:
            async with aiohttp.ClientSession(timeout=timeout) as temp_session:
                async with temp_session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        logger.warning(f"Alpaca options API error for {ticker}: status {resp.status}")
                        return []
                    data = await resp.json()
        else:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"Alpaca options API error for {ticker}: status {resp.status}")
                    return []
                data = await resp.json()
        
        snapshots = data.get("snapshots", {})
        if not snapshots:
            logger.debug(f"No option snapshots found for {ticker} ({option_type})")
            return []
        
        chain = []
        contract_symbols = list(snapshots.keys())
        quotes: dict = {}
        
        # Fetch quotes for all contracts to get bid prices
        if contract_symbols:
            quotes_url = "https://data.alpaca.markets/v1beta1/options/quotes/latest"
            quotes_params = {
                "symbols": ",".join(contract_symbols),
                "feed": "opra",
            }
            
            if session is None:
                async with aiohttp.ClientSession(timeout=timeout) as temp_session:
                    async with temp_session.get(quotes_url, headers=headers, params=quotes_params) as quotes_resp:
                        if quotes_resp.status == 200:
                            quotes_data = await quotes_resp.json()
                            quotes = quotes_data.get("quotes", {})
            else:
                async with session.get(quotes_url, headers=headers, params=quotes_params) as quotes_resp:
                    if quotes_resp.status == 200:
                        quotes_data = await quotes_resp.json()
                        quotes = quotes_data.get("quotes", {})
        
        # Parse each contract symbol and build chain
        for contract_symbol, snapshot in snapshots.items():
            parsed = _parse_contract_symbol(contract_symbol)
            if not parsed:
                continue
            
            # Filter by option type
            if parsed["option_type"] != option_type.lower():
                continue
            
            # Get bid price from quotes (use latestQuote as fallback)
            bid = 0.0
            if contract_symbol in quotes:
                quote = quotes[contract_symbol]
                bid = float(quote.get("bp", 0))  # bp = bid price
            elif "latestQuote" in snapshot:
                quote = snapshot["latestQuote"]
                bid = float(quote.get("bp", 0))
            
            # Only include contracts with valid bid
            if bid <= 0:
                continue
            
            chain.append(
                {
                    "symbol": contract_symbol,
                    "strike_price": parsed["strike_price"],
                    "expiration_date": parsed["expiration_date"],
                    "option_type": parsed["option_type"],
                    "bid": bid,
                    "ask": float(snapshot.get("latestQuote", {}).get("ap", 0)) if "latestQuote" in snapshot else 0.0,
                    "delta": None,  # Will need to fetch greeks separately if needed
                }
            )
        
        logger.info(
            f"Option chain for {ticker} ({option_type}): {len(chain)} contracts"
        )
        return chain
    except Exception as e:
        logger.error(f"Option chain error for {ticker}: {e}")
        return []
