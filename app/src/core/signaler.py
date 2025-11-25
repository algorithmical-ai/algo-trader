import aiohttp
from typing import Optional, Dict, Any
from app.src.config.settings import settings
from app.src.utils.logger import logger


async def send_signal(
    ticker: str,
    action: str,
    reason: str,
    price: Optional[float] = None,
    session: Optional[aiohttp.ClientSession] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Send signal to your execution app.
    extra = any dict (e.g., option contract symbol, strike, etc.)
    """
    payload = {
        "ticker_symbol": ticker,
        "action": action,
        "indicator": settings.INDICATOR_NAME,
        "reason": reason
    }

    if price is not None:
        payload["price"] = str(round(float(price), 2))

    if extra:
        payload.update(extra)  # Merges option_contract, strike, etc.

    try:
        if session is None:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as sess:
                async with sess.post(settings.WEBHOOK_URL, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"SIGNAL → {ticker} {action} | {reason}")
                    else:
                        text = await resp.text()
                        logger.error(f"Webhook failed {resp.status}: {text}")
        else:
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.post(settings.WEBHOOK_URL, json=payload, timeout=timeout) as resp:
                if resp.status == 200:
                    logger.info(f"SIGNAL → {ticker} {action} | {reason}")
                else:
                    text = await resp.text()
                    logger.error(f"Webhook failed {resp.status}: {text}")
    except Exception as e:
        logger.error(f"Signal send error: {e}")