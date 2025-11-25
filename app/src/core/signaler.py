import aiohttp
from app.src.config.settings import settings
from app.src.utils.logger import logger


async def send_signal(
    ticker: str,
    action: str,
    reason: str,
    price: float | None = None,
    session: aiohttp.ClientSession = None,
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
        async with session.post(
            settings.WEBHOOK_URL, json=payload, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 200:
                logger.info(
                    f"SIGNAL SENT: {ticker} {action} | {reason} | Price: ${price:.2f}"
                    if price
                    else f"SIGNAL SENT: {ticker} {action} | {reason}"
                )
            else:
                error_text = await resp.text()
                logger.error(
                    f"Webhook failed for {ticker}: {resp.status} - {error_text}"
                )
    except Exception as e:
        logger.error(f"Signal send error for {ticker}: {e}")
