from datetime import datetime
import pytz
from app.src.config.settings import settings
NY = pytz.timezone("America/New_York")


def now_ny():
    return datetime.now(NY)


def is_trading_hours():
    now = now_ny().time()
    start = datetime.strptime(settings.TRADING_START, "%H:%M").time()
    end = datetime.strptime(settings.TRADING_END, "%H:%M").time()
    return start <= now <= end
