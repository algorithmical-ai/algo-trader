import aiohttp

from app.src.config.settings import settings
from app.src.utils.logger import logger


async def send_signal(
    ticker: str,
    action: str,
    reason: str,
    price: float | None = None,
    session: aiohttp.ClientSession | None = None,
):
    payload = {
        "ticker_symbol": ticker,
        "action": action,
        "indicator": settings.INDICATOR_NAME,
        "reason": reason,
    }
    if price:
        payload["price"] = str(round(price, 2))

    try:
        if session is None:
            async with aiohttp.ClientSession() as new_session:
                async with new_session.post(
                    settings.WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        logger.info(
                            f"SIGNAL SENT: {ticker} {action} | {reason} | Price: ${price:.2f}"
                            if price
                            else f"SIGNAL SENT: {ticker} {action} | {reason}"
                        )
        else:
            async with session.post(
                settings.WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    logger.info(
                        f"SIGNAL SENT: {ticker} {action} | {reason} | Price: ${price:.2f}"
                        if price
                        else f"SIGNAL SENT: {ticker} {action} | {reason}"
                    )
    except Exception as e:
        logger.error(f"Signal send error for {ticker}: {e}")
