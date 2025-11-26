import asyncio
from datetime import datetime

from alpaca.data.timeframe import TimeFrame

from app.src.config.settings import settings
from app.src.core.signaler import send_signal
from app.src.data.alpaca_client import get_bars
from app.src.data.option_chain import get_option_chain
from app.src.data.unusual_whales import get_iv_rank, get_screener_tickers
from app.src.indicators.options_selector import WheelOptionsSelector
from app.src.position_tracker.wheel_tracker import WheelTracker
from app.src.utils.helpers import now_ny
from app.src.utils.logger import logger


async def get_spot_price(ticker: str) -> float:
    """Get latest price from Alpaca"""
    try:
        bars = await get_bars([ticker], TimeFrame.Minute, limit=1)
        if ticker in bars.index.get_level_values(0):
            return float(bars.xs(ticker, level=0)["close"].iloc[-1])
        return 0.0
    except:
        return 0.0


async def run_weekly_put_wheel(session):
    """Runs every trading day 3:55–4:10 PM ET — sells the best cash-secured puts.

    When settings.DEBUG_OPTION is True, ignores the day/time window and runs on
    every loop (useful for local debugging).
    """
    now = now_ny()
    if settings.DEBUG_OPTION:
        logger.info(
            "WheelMaster: DEBUG_OPTION enabled — running put wheel immediately "
            "without schedule gating"
        )
    else:
        # Only run on trading days (Mon–Fri). Weekends are skipped.
        if now.weekday() > 4:
            logger.info(
                f"WheelMaster: skipping weekly put wheel — today is {now.strftime('%A')} "
                "(runs only on trading days Mon–Fri)"
            )
            return

        current_time_str = now.strftime("%H:%M")
        if not ("15:55" <= current_time_str <= "16:10"):
            logger.info(
                "WheelMaster: skipping weekly put wheel — current time "
                f"{current_time_str} ET, window is 15:55–16:10 ET"
            )
            return

        logger.info("WheelMaster: running weekly put wheel scan")

    # Every Friday, use Unusual Whales screener + your golden list
    tickers = list(
        set(await get_screener_tickers(session) + settings.BEST_2025_WHEEL_TICKERS)
    )

    for ticker in tickers:
        try:
            spot = await get_spot_price(ticker)
            if spot < 100:
                continue

            iv_rank_val = await get_iv_rank(ticker, session)
            chain = await get_option_chain(ticker, option_type="put", session=session)
            if not chain:
                continue

            best_put = WheelOptionsSelector.select_best_put(chain, spot, iv_rank_val)
            if best_put is not None:
                reason = (
                    f"Wheel Put | Δ{best_put['delta']} | {best_put['distance_pct']}% OTM | "
                    f"IVR {iv_rank_val:.0f} | Credit ${best_put['premium']:.2f}"
                )
                await send_signal(
                    ticker,
                    "sell_to_open_put",
                    reason,
                    price=best_put["premium"],
                    session=session,
                    extra={"contract": best_put["contract"]},
                    indicator="WheelMaster",
                )
                WheelTracker.record_put_sold(ticker, best_put)

        except Exception as e:
            print(f"Wheel error {ticker}: {e}")

        await asyncio.sleep(8)  # Stay under rate limits


async def check_assignment_and_sell_call(session, alpaca_positions):
    """If you got assigned shares → immediately sell covered call"""
    for pos in alpaca_positions:
        ticker = pos.symbol
        qty = int(pos.qty)
        if qty > 0 and ticker in WheelTracker.get_open_puts():
            spot = float(pos.avg_entry_price)
            chain = await get_option_chain(ticker, option_type="call", session=session)
            best_call = WheelOptionsSelector.select_best_call(chain, spot)
            if best_call is not None:
                reason = f"Wheel Call | Assigned @ ${spot:.2f} → Selling call for ${best_call['premium']:.2f}"
                await send_signal(
                    ticker,
                    "sell_to_open_call",
                    reason,
                    price=best_call["premium"],
                    session=session,
                    extra={"contract": best_call["contract"]},
                    indicator="WheelMaster",
                )
            WheelTracker.record_assignment(ticker)
