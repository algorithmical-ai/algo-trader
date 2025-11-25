from datetime import datetime
from functools import lru_cache
from typing import Optional

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

_OPEN_POSITIONS_TABLE = "AlgoTraderOpenPositions"
_COMPLETED_TRADES_TABLE = "CompletedTradesForAlgoTrader"
_INACTIVE_TICKERS_TABLE = "InactiveTickersForAlgoTrading"


@lru_cache(maxsize=1)
def _get_dynamodb_resource():
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning("AWS credentials not configured; DynamoDB operations will fail")
        return None
    try:
        return boto3.resource(
            "dynamodb",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION,
        )
    except Exception as exc:
        logger.error(f"Unable to initialize DynamoDB resource: {exc}")
        return None


class PositionTracker:
    @staticmethod
    def add_position(
        ticker: str,
        action: str,
        price: float,
        reason: str,
        indicator: Optional[str] = None,
    ):
        """Add a new open position to AlgoTraderOpenPositions table."""
        if indicator is None:
            indicator = settings.INDICATOR_NAME

        dynamodb = _get_dynamodb_resource()
        if dynamodb is None:
            logger.error("Cannot add position: DynamoDB not available")
            return

        table = dynamodb.Table(_OPEN_POSITIONS_TABLE)
        entry_timestamp = datetime.utcnow().isoformat()

        try:
            table.put_item(
                Item={
                    "ticker": ticker,
                    "indicator": indicator,
                    "action": action,
                    "entry_price": str(price),
                    "enter_reason": reason,
                    "enter_timestamp": entry_timestamp,
                }
            )
            logger.info(f"POSITION ADDED: {ticker} {action} @ ${price:.2f} | {reason}")
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"DynamoDB write failed for position {ticker}: {exc}")

    @staticmethod
    def get_position(ticker: str, indicator: Optional[str] = None) -> dict | None:
        """Get an open position from AlgoTraderOpenPositions table."""
        if indicator is None:
            indicator = settings.INDICATOR_NAME

        dynamodb = _get_dynamodb_resource()
        if dynamodb is None:
            logger.error("Cannot get position: DynamoDB not available")
            return None

        table = dynamodb.Table(_OPEN_POSITIONS_TABLE)

        try:
            response = table.get_item(
                Key={
                    "ticker": ticker,
                    "indicator": indicator,
                }
            )
            if "Item" in response:
                item = response["Item"]
                return {
                    "action": item.get("action"),
                    "entry_price": float(item.get("entry_price", 0)),
                    "reason": item.get("enter_reason"),
                    "timestamp": item.get("enter_timestamp"),
                }
            return None
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"DynamoDB read failed for position {ticker}: {exc}")
            return None

    @staticmethod
    def close_position(
        ticker: str,
        exit_action: str,
        exit_price: float,
        reason: str,
        indicator: Optional[str] = None,
    ):
        """Close a position by moving it from AlgoTraderOpenPositions to CompletedTradesForAlgoTrader."""
        if indicator is None:
            indicator = settings.INDICATOR_NAME

        dynamodb = _get_dynamodb_resource()
        if dynamodb is None:
            logger.error("Cannot close position: DynamoDB not available")
            return

        open_table = dynamodb.Table(_OPEN_POSITIONS_TABLE)
        completed_table = dynamodb.Table(_COMPLETED_TRADES_TABLE)

        try:
            # Get the open position
            response = open_table.get_item(
                Key={
                    "ticker": ticker,
                    "indicator": indicator,
                }
            )

            if "Item" not in response:
                logger.info(f"No open position for {ticker} with indicator {indicator}")
                return

            item = response["Item"]
            entry_price = float(item.get("entry_price", 0))
            entry_action = item.get("action", "")

            # Calculate profit/loss
            if "buy_to_open" in entry_action:
                profit_or_loss = exit_price - entry_price
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                profit_or_loss = entry_price - exit_price
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100

            # Build completed trade entry
            exit_timestamp = datetime.utcnow().isoformat()
            completed_trade = {
                "ticker": ticker,
                "action": entry_action,
                "entry_price": str(entry_price),
                "enter_reason": item.get("enter_reason", ""),
                "enter_timestamp": item.get("enter_timestamp", ""),
                "exit_price": str(exit_price),
                "exit_timestamp": exit_timestamp,
                "exit_reason": reason,
                "profit_or_loss": str(profit_or_loss),
            }

            # Get current date for partition key
            date_key = datetime.utcnow().date().isoformat()

            # Get existing completed trades data
            try:
                completed_response = completed_table.get_item(
                    Key={
                        "date": date_key,
                        "indicator": indicator,
                    }
                )
                if "Item" in completed_response:
                    existing_item = completed_response["Item"]
                    completed_trades = existing_item.get("completed_trades", [])
                    completed_trade_count = existing_item.get(
                        "completed_trade_count", 0
                    )
                    overall_profit_loss = float(
                        existing_item.get("overall_profit_loss", "0")
                    )
                    overall_profit_loss_long = float(
                        existing_item.get("overall_profit_loss_long", "0")
                    )
                    overall_profit_loss_short = float(
                        existing_item.get("overall_profit_loss_short", "0")
                    )
                else:
                    completed_trades = []
                    completed_trade_count = 0
                    overall_profit_loss = 0.0
                    overall_profit_loss_long = 0.0
                    overall_profit_loss_short = 0.0
            except (ClientError, BotoCoreError) as exc:
                logger.warning(f"Failed to get existing completed trades: {exc}")
                completed_trades = []
                completed_trade_count = 0
                overall_profit_loss = 0.0
                overall_profit_loss_long = 0.0
                overall_profit_loss_short = 0.0

            # Update completed trades
            completed_trades.append(completed_trade)
            completed_trade_count += 1
            overall_profit_loss += profit_or_loss

            if "buy_to_open" in entry_action:
                overall_profit_loss_long += profit_or_loss
            else:
                overall_profit_loss_short += profit_or_loss

            # Write to completed trades table
            completed_table.put_item(
                Item={
                    "date": date_key,
                    "indicator": indicator,
                    "completed_trades": completed_trades,
                    "completed_trade_count": completed_trade_count,
                    "overall_profit_loss": str(overall_profit_loss),
                    "overall_profit_loss_long": str(overall_profit_loss_long),
                    "overall_profit_loss_short": str(overall_profit_loss_short),
                }
            )

            # Delete from open positions table
            open_table.delete_item(
                Key={
                    "ticker": ticker,
                    "indicator": indicator,
                }
            )

            logger.info(
                f"POSITION CLOSED: {ticker} {exit_action} @ ${exit_price:.2f} | PnL: {pnl_pct:+.2f}% | {reason}"
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"DynamoDB close position failed for {ticker}: {exc}")

    @staticmethod
    def get_open_positions(indicator: Optional[str] = None) -> list[str]:
        """Get list of tickers with open positions."""
        if indicator is None:
            indicator = settings.INDICATOR_NAME

        dynamodb = _get_dynamodb_resource()
        if dynamodb is None:
            logger.error("Cannot get open positions: DynamoDB not available")
            return []

        table = dynamodb.Table(_OPEN_POSITIONS_TABLE)
        tickers = []

        try:
            # Scan table for all positions with the given indicator
            # Note: In production, consider using GSI if needed for better performance
            response = table.scan(
                FilterExpression="indicator = :ind",
                ExpressionAttributeValues={":ind": indicator},
            )

            for item in response.get("Items", []):
                tickers.append(item.get("ticker"))

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(
                    FilterExpression="indicator = :ind",
                    ExpressionAttributeValues={":ind": indicator},
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                for item in response.get("Items", []):
                    tickers.append(item.get("ticker"))

            return tickers
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"DynamoDB scan failed for open positions: {exc}")
            return []


class InactiveTickerTracker:
    """Track tickers that didn't enter trades with reasons and indicator values."""

    @staticmethod
    def log_inactive_ticker(
        ticker: str,
        reason_not_to_enter_long: str = "",
        reason_not_to_enter_short: str = "",
        indicators_values: Optional[dict] = None,
        indicator: Optional[str] = None,
    ):
        """
        Log an inactive ticker with reasons and indicator values.
        
        Args:
            ticker: Stock ticker symbol
            reason_not_to_enter_long: Reason why long trade was not entered
            reason_not_to_enter_short: Reason why short trade was not entered
            indicators_values: Dictionary of computed indicator values
            indicator: Indicator name (defaults to settings.INDICATOR_NAME)
        """
        if indicator is None:
            indicator = settings.INDICATOR_NAME

        dynamodb = _get_dynamodb_resource()
        if dynamodb is None:
            logger.debug("Cannot log inactive ticker: DynamoDB not available")
            return

        table = dynamodb.Table(_INACTIVE_TICKERS_TABLE)
        last_updated = datetime.utcnow().isoformat()

        # Prepare indicators_values as a dict (DynamoDB supports maps)
        indicators_dict = indicators_values if indicators_values is not None else {}

        try:
            table.put_item(
                Item={
                    "ticker": ticker,
                    "indicator": indicator,
                    "last_updated": last_updated,
                    "reason_not_to_enter_long": reason_not_to_enter_long,
                    "reason_not_to_enter_short": reason_not_to_enter_short,
                    "indicators_values": indicators_dict,
                }
            )
            logger.debug(f"Logged inactive ticker {ticker} with indicator {indicator}")
        except (ClientError, BotoCoreError) as exc:
            logger.warning(f"DynamoDB write failed for inactive ticker {ticker}: {exc}")

    @staticmethod
    def get_inactive_ticker(
        ticker: str, indicator: Optional[str] = None
    ) -> dict | None:
        """
        Get inactive ticker information.
        
        Returns:
            Dictionary with inactive ticker data or None if not found
        """
        if indicator is None:
            indicator = settings.INDICATOR_NAME

        dynamodb = _get_dynamodb_resource()
        if dynamodb is None:
            logger.debug("Cannot get inactive ticker: DynamoDB not available")
            return None

        table = dynamodb.Table(_INACTIVE_TICKERS_TABLE)

        try:
            response = table.get_item(
                Key={
                    "ticker": ticker,
                    "indicator": indicator,
                }
            )
            if "Item" in response:
                item = response["Item"]
                return {
                    "last_updated": item.get("last_updated"),
                    "reason_not_to_enter_long": item.get("reason_not_to_enter_long", ""),
                    "reason_not_to_enter_short": item.get("reason_not_to_enter_short", ""),
                    "indicators_values": item.get("indicators_values", {}),
                }
            return None
        except (ClientError, BotoCoreError) as exc:
            logger.warning(f"DynamoDB read failed for inactive ticker {ticker}: {exc}")
            return None
