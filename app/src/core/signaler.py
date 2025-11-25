import asyncio
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

import aiohttp

# Import legacy_cgi before boto3 to provide cgi module for Python 3.13+
try:
    import sys

    import legacy_cgi  # noqa: F401
    if "cgi" not in sys.modules:
        sys.modules["cgi"] = legacy_cgi
except ImportError:
    pass  # Not needed for Python < 3.13

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.src.config.settings import settings
from app.src.utils.logger import logger

_DYNAMO_TABLE_NAME = "AlgoOptions"
_OPTION_ACTION_MAPPING = {
    "sell_to_open_put": "sell_to_open_put",
    "sell_to_open_call": "sell_to_open_call",
}


@lru_cache(maxsize=1)
def _get_dynamo_table():
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning("AWS credentials not configured; skipping DynamoDB logging")
        return None
    try:
        dynamodb = boto3.resource(
            "dynamodb",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION,
        )
        return dynamodb.Table(_DYNAMO_TABLE_NAME)
    except Exception as exc:
        logger.error(f"Unable to initialize DynamoDB table {_DYNAMO_TABLE_NAME}: {exc}")
        return None


def _coerce_profit(value: Optional[Any]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_option_entry(
    ticker: str,
    action: str,
    reason: str,
    extra: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    est_now = datetime.now(ZoneInfo("America/New_York"))
    profit_value = None
    expiry_value = None
    if extra:
        profit_value = _coerce_profit(extra.get("profit"))
        expiry_value = extra.get("expiry")

    return {
        "ticker_symbol": ticker,
        "action": action,
        "reason": reason,
        "profit": profit_value,
        "expiry": expiry_value,
        "timestamp": est_now.isoformat(),
    }


def _write_option_signal(
    ticker: str,
    action: str,
    reason: str,
    indicator: str,
    extra: Optional[Dict[str, Any]],
):
    if action not in _OPTION_ACTION_MAPPING:
        return

    table = _get_dynamo_table()
    if table is None:
        return

    entry = _build_option_entry(ticker, action, reason, extra)
    date_key = entry["timestamp"][:10]
    action_column = _OPTION_ACTION_MAPPING[action]

    try:
        table.update_item(
            Key={"date": date_key, "indicator": indicator},
            UpdateExpression=(
                f"SET #{action_column} = list_append("
                f"if_not_exists(#{action_column}, :empty_list), :entry)"
            ),
            ExpressionAttributeNames={f"#{action_column}": action_column},
            ExpressionAttributeValues={
                ":entry": [entry],
                ":empty_list": [],
            },
        )
    except (ClientError, BotoCoreError) as exc:
        logger.error(f"DynamoDB write failed for {ticker} {action}: {exc}")


async def send_signal(
    ticker: str,
    action: str,
    reason: str,
    price: Optional[float] = None,
    session: Optional[aiohttp.ClientSession] = None,
    extra: Optional[Dict[str, Any]] = None,
):
    """
    Send signal to your execution app.
    extra = any dict (e.g., option contract symbol, strike, etc.)
    """
    payload = {
        "ticker_symbol": ticker,
        "action": action,
        "indicator": settings.INDICATOR_NAME,
        "reason": reason,
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
            async with session.post(
                settings.WEBHOOK_URL, json=payload, timeout=timeout
            ) as resp:
                if resp.status == 200:
                    logger.info(f"SIGNAL → {ticker} {action} | {reason}")
                else:
                    text = await resp.text()
                    logger.error(f"Webhook failed {resp.status}: {text}")
    except Exception as e:
        logger.error(f"Signal send error: {e}")
    finally:
        await asyncio.to_thread(
            _write_option_signal,
            ticker,
            action,
            reason,
            settings.INDICATOR_NAME,
            extra,
        )
