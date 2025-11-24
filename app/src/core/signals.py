from datetime import datetime
from src.indicators.talib_wrapper import rsi
from src.utils.logger import logger
import numpy as np


def generate_signal(symbol: str, df) -> dict | None:
    if len(df) < 100:
        return None

    close = df["close"].values[-50:]
    volume = df["volume"].values[-1]

    current_rsi = rsi(close)[-1]
    prev_rsi = rsi(close[:-1])[-1]

    price = close[-1]

    # Simple but effective 2025 strategy
    if prev_rsi < 30 and current_rsi >= 30 and volume > 1_000_000:
        return {
            "symbol": symbol,
            "side": "buy",
            "price": round(float(price), 2),
            "reason": f"RSI bullish crossover ({prev_rsi:.1f} → {current_rsi:.1f}) + high volume",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    if prev_rsi > 70 and current_rsi <= 70 and volume > 1_000_000:
        return {
            "symbol": symbol,
            "side": "sell",
            "price": round(float(price), 2),
            "reason": f"RSI bearish crossover ({prev_rsi:.1f} → {current_rsi:.1f}) + high volume",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    return None
