import os
from dotenv import load_dotenv
from ..logger import logger

load_dotenv()


class Settings:
    ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
    ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
    UW_API_KEY = os.getenv("UNUSUAL_WHALES_API_KEY")
    REDIS_URL = os.getenv("REDIS_URL")
    WEBHOOK_URL = (
        "https://tradingview-webhook-maverick-d375f5273444.herokuapp.com/webhook"
    )
    INDICATOR_NAME = "AlgoTrader_Elite_2025"

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

    MIN_PRICE = 8.0
    MIN_RVOL = 7.0
    ORB_MINUTES = 15
    MIN_FLOW_PREMIUM = 40000
    TRADING_START = "09:30"
    TRADING_END = "15:55"
    ORB_PHASE_END = "10:30"


settings = Settings()

if not all([settings.ALPACA_KEY, settings.ALPACA_SECRET]):
    logger.error("Missing Alpaca keys in .env")
    raise ValueError("Configure .env")
