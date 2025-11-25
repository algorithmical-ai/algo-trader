import asyncio
import re
from datetime import datetime

import aiohttp

from app.src.config.settings import settings
from app.src.utils.logger import logger


async def get_flow_signal(ticker: str, session: aiohttp.ClientSession):
    """Enhanced flow with sweeps, openers, and sentiment using new API."""
    url = "https://api.unusualwhales.com/api/option-trades/flow-alerts"
    headers = {
        "Accept": "application/json, text/plain",
        "Authorization": f"Bearer {settings.UW_API_KEY}",
    }
    params = {"ticker_symbol": ticker}

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(
            url, headers=headers, params=params, timeout=timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                alerts = data.get("data", [])
                if not alerts:
                    return None
                
                # Process the most recent alerts (they're already sorted by date)
                for alert in alerts[:5]:  # Check top 5 alerts
                    try:
                        # Parse total_premium as string, remove commas
                        premium_str = str(alert.get("total_premium", "0")).replace(",", "")
                        premium = float(premium_str) if premium_str else 0.0
                        
                        # Check if premium meets threshold
                        if premium >= settings.MIN_FLOW_PREMIUM:
                            alert_type = alert.get("type", "").lower()
                            has_sweep = alert.get("has_sweep", False)
                            
                            # Check bid/ask side premium for direction
                            bid_prem_str = str(alert.get("total_bid_side_prem", "0")).replace(",", "")
                            ask_prem_str = str(alert.get("total_ask_side_prem", "0")).replace(",", "")
                            bid_prem = float(bid_prem_str) if bid_prem_str else 0.0
                            ask_prem = float(ask_prem_str) if ask_prem_str else 0.0
                            
                            # Determine sentiment based on type, premium flow, and sweep activity
                            # More bid side premium = bullish (buying pressure)
                            # More ask side premium = bearish (selling pressure)
                            if bid_prem > 0 or ask_prem > 0:
                                # If bid premium is significantly higher, it's bullish
                                if bid_prem > ask_prem * 1.2:  # 20% more bid than ask
                                    return "bullish"
                                # If ask premium is significantly higher, it's bearish
                                elif ask_prem > bid_prem * 1.2:  # 20% more ask than bid
                                    return "bearish"
                            
                            # Fallback to option type if bid/ask analysis inconclusive
                            if alert_type == "call":
                                # Call buying is bullish, but check if it's a sweep (aggressive buying)
                                if has_sweep:
                                    return "bullish"
                                # Regular call flow - still bullish but less aggressive
                                return "bullish"
                            elif alert_type == "put":
                                # Put buying can be bearish (speculation) or bullish (hedging)
                                # If it's a sweep, it's likely bearish speculation
                                if has_sweep:
                                    return "bearish"
                                # Regular put flow - could be hedging, less clear signal
                                return "bearish"
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Error parsing flow alert for {ticker}: {e}")
                        continue
            elif resp.status == 404:
                # No flow alerts for this ticker
                return None
            else:
                logger.warning(f"UW flow fetch error for {ticker}: status {resp.status}")
            return None
    except Exception as e:
        logger.warning(f"UW flow fetch error for {ticker}: {e}")
        return None


async def get_congress_trades(ticker: str, session: aiohttp.ClientSession):
    """Politician trades for edge (buy if they buy) using new API."""
    # Use today's date for the query
    today = datetime.now().strftime("%Y-%m-%d")
    url = "https://api.unusualwhales.com/api/congress/recent-trades"
    headers = {
        "Accept": "application/json, text/plain",
        "Authorization": f"Bearer {settings.UW_API_KEY}",
    }
    params = {"ticker": ticker, "date": today}

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(
            url, headers=headers, params=params, timeout=timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                trades = data.get("data", [])
                if not trades:
                    return None
                
                # Check recent trades (within last 7 days)
                for trade in trades:
                    txn_type = trade.get("txn_type", "").upper()
                    amounts_str = trade.get("amounts", "")
                    is_active = trade.get("is_active", False)
                    
                    # Parse amount range (e.g., "$15,001 - $50,000")
                    # Extract the minimum value from the range
                    try:
                        if amounts_str and "-" in amounts_str:
                            # Extract first number from range
                            min_amount_str = amounts_str.split("-")[0].strip()
                            # Remove $ and commas
                            min_amount_str = min_amount_str.replace("$", "").replace(",", "")
                            min_amount = float(min_amount_str) if min_amount_str else 0.0
                        else:
                            # Try to extract any number from the string
                            numbers = re.findall(r'\d+', amounts_str.replace(",", ""))
                            min_amount = float(numbers[0]) if numbers else 0.0
                    except (ValueError, AttributeError):
                        min_amount = 0.0
                    
                    # Only consider active trades with significant amounts
                    if (
                        txn_type == "BUY"
                        and is_active
                        and min_amount >= settings.MIN_CONGRESS_TRADE_AMOUNT
                    ):
                        return "bullish"
                    elif (
                        txn_type == "SELL"
                        and is_active
                        and min_amount >= settings.MIN_CONGRESS_TRADE_AMOUNT
                    ):
                        return "bearish"
                return None
            elif resp.status == 404:
                # No congress trades for this ticker
                return None
            else:
                logger.warning(f"UW congress error for {ticker}: status {resp.status}")
            return None
    except Exception as e:
        logger.warning(f"UW congress error for {ticker}: {e}")
        return None


async def get_dark_pool(ticker: str, session: aiohttp.ClientSession):
    """Dark pool volume for institutional support using new API."""
    url = f"https://api.unusualwhales.com/api/darkpool/{ticker}"
    headers = {
        "Accept": "application/json, text/plain",
        "Authorization": f"Bearer {settings.UW_API_KEY}",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json()
                trades = data.get("data", [])
                if not trades:
                    return None
                
                # Filter out canceled trades and calculate totals
                valid_trades = [t for t in trades if not t.get("canceled", False)]
                if not valid_trades:
                    return None
                
                total_premium = sum(float(str(t.get("premium", "0")).replace(",", "")) for t in valid_trades)
                total_size = sum(int(t.get("size", 0)) for t in valid_trades)
                
                # Check if dark pool activity meets threshold
                if total_premium >= settings.MIN_DARK_POOL_PREMIUM or total_size >= settings.MIN_DARK_POOL_SIZE:
                    # Analyze price action: if price is near NBBO bid, it's likely bullish
                    # If price is near NBBO ask, it's likely bearish
                    bullish_count = 0
                    bearish_count = 0
                    
                    for trade in valid_trades[:10]:  # Check top 10 trades
                        try:
                            price = float(trade.get("price", 0))
                            nbbo_bid = float(trade.get("nbbo_bid", 0))
                            nbbo_ask = float(trade.get("nbbo_ask", 0))
                            
                            if nbbo_bid > 0 and nbbo_ask > 0:
                                # If trade price is closer to bid, it's likely a buy (bullish)
                                # If trade price is closer to ask, it's likely a sell (bearish)
                                bid_distance = abs(price - nbbo_bid) / nbbo_bid if nbbo_bid > 0 else 1.0
                                ask_distance = abs(price - nbbo_ask) / nbbo_ask if nbbo_ask > 0 else 1.0
                                
                                if bid_distance < ask_distance * 0.8:  # Closer to bid
                                    bullish_count += 1
                                elif ask_distance < bid_distance * 0.8:  # Closer to ask
                                    bearish_count += 1
                        except (ValueError, TypeError):
                            continue
                    
                    if bullish_count > bearish_count * 1.5:
                        return "bullish"
                    elif bearish_count > bullish_count * 1.5:
                        return "bearish"
                    # Default to bullish for large dark pool prints (institutional accumulation)
                    elif total_premium >= settings.MIN_DARK_POOL_PREMIUM:
                        return "bullish"
                return None
            elif resp.status == 404:
                # No dark pool data for this ticker
                return None
            else:
                logger.warning(f"UW dark pool error for {ticker}: status {resp.status}")
            return None
    except Exception as e:
        logger.warning(f"UW dark pool error for {ticker}: {e}")
        return None


async def get_iv_rank(ticker: str, session: aiohttp.ClientSession, max_retries: int = 3):
    """IV percentile for volatility filter using new API."""
    url = f"https://api.unusualwhales.com/api/stock/{ticker}/iv-rank"
    headers = {
        "Accept": "application/json, text/plain",
        "Authorization": f"Bearer {settings.UW_API_KEY}",
    }

    for attempt in range(max_retries):
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Response has a "data" array with most recent entry first
                    data_array = data.get("data", [])
                    if data_array and len(data_array) > 0:
                        # Get the most recent IV rank (first item in array)
                        iv_str = data_array[0].get("iv_rank_1y", "0")
                        try:
                            # IV rank is already a percentage (e.g., "18.6661" = 18.67%)
                            iv_rank = float(iv_str) if iv_str not in ("N/A", None, "") else 0.0
                        except (ValueError, TypeError):
                            iv_rank = 0.0
                        return iv_rank
                    return 0.0
                elif 400 <= resp.status < 500:
                    # 4xx error - retry with backoff
                    if attempt < max_retries - 1:
                        # Use longer backoff for rate limits (429)
                        backoff_time = 2 if resp.status == 429 else 1
                        logger.warning(
                            f"UW IV rank 4xx error for {ticker}: status {resp.status}, retrying ({attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        logger.error(f"UW IV rank failed for {ticker} after {max_retries} attempts: status {resp.status}")
                        return 0.0
                else:
                    # Non-4xx error, don't retry
                    logger.warning(f"UW IV rank error for {ticker}: status {resp.status}")
                    return 0.0
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"UW IV rank exception for {ticker}: {e}, retrying ({attempt + 1}/{max_retries})")
                await asyncio.sleep(1)
                continue
            else:
                logger.warning(f"UW IV rank error for {ticker} after {max_retries} attempts: {e}")
                return 0.0
    
    return 0.0


async def get_screener_tickers(session: aiohttp.ClientSession):
    """Dynamic watchlist from stock screener using new API."""
    # Use today's date for the query
    today = datetime.now().strftime("%Y-%m-%d")
    url = "https://api.unusualwhales.com/api/screener/stocks"
    headers = {
        "Accept": "application/json, text/plain",
        "Authorization": f"Bearer {settings.UW_API_KEY}",
    }
    # Screen for S&P 500 stocks with high volume and unusual flow
    params = {
        "is_s_p_500": "true",  # String value for API
        "date": today,
        "limit": "50",  # Get more tickers to filter - must be string
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with session.get(
            url,
            headers=headers,
            params=params,
            timeout=timeout,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                stocks = data.get("data", [])
                if not stocks:
                    return settings.WATCHLIST  # Fallback
                
                # Filter by relative volume and unusual flow
                filtered_tickers = []
                for stock in stocks:
                    ticker = stock.get("ticker")
                    if not ticker:
                        continue
                    
                    # Check for high relative volume
                    rvol = float(stock.get("relative_volume", 0))
                    # Check for unusual call/put premium
                    call_premium = float(str(stock.get("call_premium", "0")).replace(",", ""))
                    put_premium = float(str(stock.get("put_premium", "0")).replace(",", ""))
                    total_premium = call_premium + put_premium
                    
                    # Filter criteria: high relative volume OR high options premium
                    if rvol >= 1.2 or total_premium >= 10000000:  # 1.2x volume or $10M+ premium
                        filtered_tickers.append(ticker)
                    
                    # Limit to top 20 tickers
                    if len(filtered_tickers) >= 20:
                        break
                
                if filtered_tickers:
                    logger.info(f"Screener found {len(filtered_tickers)} tickers: {filtered_tickers[:10]}")
                    return filtered_tickers
                else:
                    return settings.WATCHLIST  # Fallback
            else:
                logger.warning(f"UW screener error: status {resp.status}")
                return settings.WATCHLIST  # Fallback
    except Exception as e:
        logger.warning(f"UW screener error: {e}")
        return settings.WATCHLIST  # Fallback
