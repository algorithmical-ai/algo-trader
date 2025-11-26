import functools
import inspect
from datetime import datetime, time
from time import perf_counter
from typing import Any, Callable

import pytz

from app.src.utils.logger import logger

NY = pytz.timezone("America/New_York")


def now_ny():
    return datetime.now(NY)


def is_trading_hours(trading_start: str, trading_end: str) -> bool:
    now = now_ny().time()
    start = time.fromisoformat(trading_start)
    end = time.fromisoformat(trading_end)
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



def measure_latency(func: Callable) -> Callable:
    """
    Decorator to measure and log the execution latency of async functions.

    Usage:
        @measure_latency
        async def my_function():
            ...

    Args:
        func: The async function to measure

    Returns:
        Wrapped function that logs execution time
    """
    if not hasattr(func, "__name__"):
        return func

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = perf_counter()
        func_name = func.__name__
        # Handle both classmethods (args[0] is a class) and instance methods (args[0] is an instance)
        if args and hasattr(args[0], "__class__"):
            if inspect.isclass(args[0]):
                # For classmethods, args[0] is the class itself
                class_name = args[0].__name__
            else:
                # For instance methods, args[0] is an instance
                class_name = args[0].__class__.__name__
        else:
            class_name = ""
        display_name = f"{class_name}.{func_name}" if class_name else func_name

        try:
            result = await func(*args, **kwargs)
            elapsed_time = perf_counter() - start_time
            logger.info(f"⏱️  {display_name} completed in {elapsed_time:.3f}s")
            return result
        except Exception as e:
            elapsed_time = perf_counter() - start_time
            logger.warning(f"⏱️  {display_name} failed after {elapsed_time:.3f}s: {str(e)}")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = perf_counter()
        func_name = func.__name__
        # Handle both classmethods (args[0] is a class) and instance methods (args[0] is an instance)
        if args and hasattr(args[0], "__class__"):
            if inspect.isclass(args[0]):
                # For classmethods, args[0] is the class itself
                class_name = args[0].__name__
            else:
                # For instance methods, args[0] is an instance
                class_name = args[0].__class__.__name__
        else:
            class_name = ""
        display_name = f"{class_name}.{func_name}" if class_name else func_name

        try:
            result = func(*args, **kwargs)
            elapsed_time = perf_counter() - start_time
            logger.info(f"⏱️  {display_name} completed in {elapsed_time:.3f}s")
            return result
        except Exception as e:
            elapsed_time = perf_counter() - start_time
            logger.warning(f"⏱️  {display_name} failed after {elapsed_time:.3f}s: {str(e)}")
            raise

    # Check if function is a coroutine function (async)
    if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE flag
        return async_wrapper
    else:
        return sync_wrapper
