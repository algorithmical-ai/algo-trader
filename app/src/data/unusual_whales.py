import aiohttp
from ..config.settings import settings
from ..logger import logger


async def get_flow_signal(ticker: str, session: aiohttp.ClientSession):
    url = "https://api.unusualwhales.com/api/v1/flowAlerts"
    headers = {"Authorization": f"Bearer {settings.UW_API_KEY}"}
    params = {"ticker": ticker, "limit": 5, "sort": "desc"}

    try:
        async with session.get(
            url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                for alert in data.get("data", []):
                    premium = float(alert.get("total_premium", 0))
                    sentiment = alert.get("sentiment", "").lower()
                    if (
                        premium >= settings.MIN_FLOW_PREMIUM
                        and "opener" in alert.get("type", "").lower()
                    ):
                        if "bullish" in sentiment:
                            return "bullish"
                        elif "bearish" in sentiment:
                            return "bearish"
            return None
    except Exception as e:
        logger.warning(f"UW flow fetch error for {ticker}: {e}")
        return None
