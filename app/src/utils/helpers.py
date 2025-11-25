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


def get_dynamic_min_rvol() -> float:
    """Calculate MIN_RVOL based on current time of day.
    
    RVOL varies throughout the trading day:
    - 9:30-10:30: 0.3-0.8x (use 0.3)
    - 10:30-12:00: 0.8-1.4x (use 0.8)
    - 12:00-14:00: 1.4-2.5x (use 1.2)
    - 14:00-15:00: Early power hour, 1.5-2.5x (use 1.5)
    - 15:00-16:00: Power hour peak, 2.5-6.0x (use 2.0)
    """
    now = now_ny().time()
    
    # 9:30-10:30: Early morning, low volume
    if time(9, 30) <= now < time(10, 30):
        return 0.3
    
    # 10:30-12:00: Mid-morning, moderate volume
    if time(10, 30) <= now < time(12, 0):
        return 0.8
    
    # 12:00-14:00: Lunch/afternoon, higher volume
    if time(12, 0) <= now < time(14, 0):
        return 1.2
    
    # 14:00-15:00: Early power hour, volume building
    if time(14, 0) <= now < time(15, 0):
        return 1.2
    
    # 15:00-16:00: Power hour peak, highest volume
    if time(15, 0) <= now <= time(16, 0):
        return 2.0
    
    # Default fallback
    return 0.7
