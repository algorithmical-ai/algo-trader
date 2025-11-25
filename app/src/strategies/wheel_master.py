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
    """Runs every Friday 3:55–4:10 PM ET — sells the best cash-secured puts"""
    if now_ny().weekday() != 4 or not (
        "15:55" <= now_ny().strftime("%H:%M") <= "16:10"
    ):
        return

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
            chain = await get_option_chain(ticker)  # ← You’ll plug real chain here
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
            chain = await get_option_chain(ticker)
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
                )
            WheelTracker.record_assignment(ticker)
