from datetime import datetime, time

import pytz

from app.src.config.settings import settings

NY = pytz.timezone("America/New_York")


def now_ny():
    return datetime.now(NY)


def is_trading_hours():
    now = now_ny().time()
    start = time.fromisoformat(settings.TRADING_START)
    end = time.fromisoformat(settings.TRADING_END)
    return start <= now <= end
