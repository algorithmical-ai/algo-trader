import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from app.src.utils.logger import logger

load_dotenv()


def _now_ny() -> datetime:
    """Return current New York time without importing helpers to avoid circular imports."""
    return datetime.now(ZoneInfo("America/New_York"))


class Settings:
    ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
    ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
    UW_API_KEY = os.getenv("UNUSUAL_WHALES_API_KEY")
    REDIS_URL = os.getenv("REDIS_URL", "")
    WEBHOOK_URL = (
        "https://tradingview-webhook-maverick-d375f5273444.herokuapp.com/webhook"
    )
    INDICATOR_NAME = "AlgoTrader_Elite_2025"
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    WATCHLIST = [
        "SPY",
        "QQQ",
        "IWM",
        "TQQQ",
        "SQQQ",
        "NVDA",
        "TSLA",
        "AAPL",
        "AMD",
        "META",
        "AMZN",
        "GOOGL",
        "MSFT",
        "NFLX",
        "SMCI",
        "AVGO",
        "ASML",
        "ARM",
        "MU",
        "KLAC",
        "LRCX",
        "MRVL",
        "PLTR",
        "SNOW",
        "CRWD",
        "GME",
        "AMC",
        "HOOD",
        "COIN",
        "MARA",
        "RIOT",
        "CLSK",
        "BABA",
        "PDD",
        "NIO",
        "XPEV",
        "LI",
        "MRNA",
        "BNTX",
        "NVAX",
        "VKTX",
        "HIMS",
        "SOFI",
        "UPST",
        "AFRM",
        "SQ",
        "PYPL",
        "XOM",
        "CVX",
        "OXY",
        "SLB",
        "FCX",
        "WMT",
        "TGT",
        "COST",
        "HD",
        "LOW",
        "RBLX",
        "DKNG",
        "U",
        "PATH",
        "IONQ",
        "RGTI",
        "ASTS",
        "SOUN",
        "UP",
        "RIVN",
        "LCID",
        "SHOP",
        "SE",
        "NET",
        "ZS",
        "PANW",
        "FTNT",
        "DDOG",
        "MDB",
        "AI",
        "SYM",
    ]

    BLOCKED_TICKERS = {"SPY", "QQQ", "IWM", "TQQQ", "SQQQ"}

    BEST_2025_WHEEL_TICKERS = [
        "NVDA",
        "TSLA",
        "AMD",
        "SMCI",
        "ARM",
        "HOOD",
        "COIN",
        "MARA",
        "RIOT",
        "CLSK",
        "UPST",
        "SOFI",
        "AFRM",
        "PATH",
        "RBLX",
        "DKNG",
        "IONQ",
        "RGTI",
        "ASTS",
        "SOUN",
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "META",
        "AVGO",
        "NFLX",
        "ADBE",
        "CRM",
        "ORCL",
        "NOW",
        "PANW",
        "CRWD",
        "ZS",
        "NET",
        "DDOG",
        "MDB",
        "SNOW",
        "PLTR",
        "AI",
        "GME",
        "AMC",
        "SPY",
        "QQQ",
        "IWM",
        "TNA",
        "SQQQ",
        "TQQQ",
        "XLF",
        "KRE",
    ]

    MIN_PRICE = 0.5
    MIN_RVOL = 0.2 if _now_ny().hour < 11 else 0.7  # Low in early, higher later
    ORB_MINUTES = 15
    # Flow alert thresholds - more realistic for actual trading
    MIN_FLOW_PREMIUM = 50000  # $50k minimum premium for significant flow
    # Congress trade thresholds
    MIN_CONGRESS_TRADE_AMOUNT = 1000  # $1k minimum (lower threshold for more signals)
    # Dark pool thresholds
    MIN_DARK_POOL_PREMIUM = 100000  # $100k minimum premium
    MIN_DARK_POOL_SIZE = 5000  # 5k shares minimum
    # IV rank threshold - allow lower IV for more opportunities
    MIN_IV_RANK = 10.0  # Lowered from 15.0 to 10.0 for more trades
    TRADING_START = "09:30"
    TRADING_END = "15:55"
    ORB_PHASE_END = "10:30"

    # Debug flag to force options strategies to run immediately (e.g., on laptop)
    DEBUG_OPTION = os.getenv("DEBUG_OPTION", "false").lower() == "true"


settings = Settings()

if not all([settings.ALPACA_KEY, settings.ALPACA_SECRET]):
    logger.error("Missing Alpaca keys in .env")
    raise ValueError("Configure .env")
