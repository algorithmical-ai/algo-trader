import talib
import numpy as np


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    return talib.RSI(close, timeperiod=period)


def sma(close: np.ndarray, period: int = 20) -> np.ndarray:
    return talib.SMA(close, timeperiod=period)
