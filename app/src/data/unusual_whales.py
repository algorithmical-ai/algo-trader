import asyncio

import aiohttp

from app.src.config.settings import settings
from app.src.utils.logger import logger


async def get_flow_signal(ticker: str, session: aiohttp.ClientSession):
    """Enhanced flow with sweeps, openers, and sentiment."""
    url = "https://api.unusualwhales.com/api/v1/flowAlerts"
    headers = {"Authorization": f"Bearer {settings.UW_API_KEY}"}
    params = {
        "ticker": ticker,
        "limit": 5,
        "sort": "desc",
        "type": "sweep,block,opener",
    }

    try:
        # Ensure all param values are strings or compatible with aiohttp
        params_str = {k: str(v) for k, v in params.items()}
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(
            url, headers=headers, params=params_str, timeout=timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                for alert in data.get("data", []):
                    premium = float(alert.get("total_premium", 0))
                    sentiment = alert.get("sentiment", "").lower()
                    if premium >= settings.MIN_FLOW_PREMIUM and (
                        "opener" in alert.get("type", "")
                        or "sweep" in alert.get("type", "")
                    ):
                        if "bullish" in sentiment or "call" in alert.get("side", ""):
                            return "bullish"
                        elif "bearish" in sentiment or "put" in alert.get("side", ""):
                            return "bearish"
            return None
    except Exception as e:
        logger.warning(f"UW flow fetch error for {ticker}: {e}")
        return None


async def get_congress_trades(ticker: str, session: aiohttp.ClientSession):
    """New: Politician trades for edge (buy if they buy)."""
    url = "https://api.unusualwhales.com/api/v1/congressTrades"
    headers = {"Authorization": f"Bearer {settings.UW_API_KEY}"}
    params = {"ticker": ticker, "limit": 10, "days": 7, "sort": "desc"}

    try:
        # Ensure all param values are strings or compatible with aiohttp
        params_str = {k: str(v) for k, v in params.items()}
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(
            url, headers=headers, params=params_str, timeout=timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                for trade in data.get("data", []):
                    if (
                        trade.get("transaction_type") == "buy"
                        and float(trade.get("amount", 0)) > 10000
                    ):
                        return "bullish"
                return None
    except Exception as e:
        logger.warning(f"UW congress error for {ticker}: {e}")
        return None


async def get_dark_pool(ticker: str, session: aiohttp.ClientSession):
    """New: Dark pool volume for institutional support."""
    url = "https://api.unusualwhales.com/api/v1/darkPoolPrints"
    headers = {"Authorization": f"Bearer {settings.UW_API_KEY}"}
    params = {"ticker": ticker, "limit": 5, "sort": "desc"}

    try:
        # Ensure params are str values for aiohttp compatibility
        params_str = {k: str(v) for k, v in params.items()}
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(
            url, headers=headers, params=params_str, timeout=timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                total_vol = sum(float(d.get("volume", 0)) for d in data.get("data", []))
                if total_vol > 100000:  # High institutional interest
                    return (
                        "bullish" if "buy" in str(data) else "bearish"
                    )  # Simple sentiment
                return None
    except Exception as e:
        logger.warning(f"UW dark pool error for {ticker}: {e}")
        return None


async def get_iv_rank(ticker: str, session: aiohttp.ClientSession, max_retries: int = 3):
    """New: IV percentile for volatility filter."""
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
                            # Convert string like "0.65" to float (65%)
                            iv_rank = float(iv_str) * 100 if iv_str not in ("N/A", None, "") else 0.0
                        except (ValueError, TypeError):
                            iv_rank = 0.0
                        return iv_rank
                    return 0.0
                elif 400 <= resp.status < 500:
                    # 4xx error - retry with backoff
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"UW IV rank 4xx error for {ticker}: status {resp.status}, retrying ({attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(1)
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
    """New: Dynamic watchlist from stock screener (high vol + flow)."""
    url = "https://api.unusualwhales.com/api/v1/stockScreener"
    headers = {"Authorization": f"Bearer {settings.UW_API_KEY}"}
    params = {"filters": "high_volume,unusual_flow", "limit": 10, "days": 70}

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(
            url,
            headers=headers,
            params={k: str(v) for k, v in params.items()},
            timeout=timeout,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return [d.get("ticker") for d in data.get("data", [])]
            return settings.WATCHLIST  # Fallback
    except Exception as e:
        logger.warning(f"UW screener error: {e}")
        return settings.WATCHLIST
