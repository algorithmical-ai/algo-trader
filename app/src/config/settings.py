from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
    ALPACA_PAPER = os.getenv("ALPACA_PAPER", "false").lower() == "true"
    ALPACA_BASE_URL = (
        "https://paper-api.alpaca.markets"
        if ALPACA_PAPER
        else "https://api.alpaca.markets"
    )

    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # TradingView or your own endpoint

    REDIS_URL = os.getenv("REDIS_URL")  # Heroku Redis / RedisToGo / etc.

    # Strategy parameters
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    MIN_VOLUME = 500_000


settings = Settings()
