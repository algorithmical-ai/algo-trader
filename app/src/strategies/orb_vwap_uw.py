from app.src.core.signaler import send_signal
from app.src.position_tracker.redis_tracker import PositionTracker
from app.src.indicators.technical import *
from app.src.data.unusual_whales import get_bullish_bearish_flow
from app.src.common.logger import logger


async def evaluate_ticker(ticker: str, df_1m, df_daily, session):
    try:
        if ticker not in df_1m.index.get_level_values(0):
            return
        df_1m_t = df_1m.xs(ticker, level=0)
        df_daily_t = (
            df_daily.xs(ticker, level=0)
            if ticker in df_daily.index.get_level_values(0)
            else None
        )
        if not df_daily_t or len(df_daily_t) < 200:
            return

        today_df = df_1m_t[df_1m_t.index.date == now_ny().date()]
        if len(today_df) < 10:
            return

        price = today_df["close"].iloc[-1]
        if price < settings.MIN_PRICE:
            return

        rvol = calculate_rvol(df_1m_t)
        if rvol < settings.MIN_RVOL:
            return

        orb_high, orb_low = get_opening_range(today_df, settings.ORB_MINUTES)
        if not orb_high:
            return

        vwap = calculate_vwap(today_df)
        flow = await get_bullish_bearish_flow(ticker, session)

        pos = PositionTracker.get_position(ticker)
        current_time = now_ny().time()

        # === ENTRY LOGIC ===
        if not pos:
            if current_time <= datetime.strptime("10:30", "%H:%M").time():
                if (
                    price > orb_high
                    and price > vwap
                    and is_uptrend(df_daily_t)
                    and flow == "bullish"
                ):
                    reason = f"ORB Breakout ↑ + Bullish Flow + RVOL {rvol:.1f}x"
                    PositionTracker.add_position(ticker, "buy_to_open", price, reason)
                    await send_signal(ticker, "buy_to_open", reason, price, session)

                elif (
                    price < orb_low
                    and price < vwap
                    and is_downtrend(df_daily_t)
                    and flow == "bearish"
                ):
                    reason = f"ORB Breakdown ↓ + Bearish Flow + RVOL {rvol:.1f}x"
                    PositionTracker.add_position(ticker, "sell_to_open", price, reason)
                    await send_signal(ticker, "sell_to_open", reason, price, session)

            # After 10:30 → VWAP Reversion
            elif current_time <= datetime.strptime("15:30", "%H:%M").time():
                if price < vwap and is_uptrend(df_daily_t) and flow == "bullish":
                    reason = f"VWAP Long Reversion + Bullish Flow"
                    PositionTracker.add_position(ticker, "buy_to_open", price, reason)
                    await send_signal(ticker, "buy_to_open", reason, price, session)

                elif price > vwap and is_downtrend(df_daily_t) and flow == "bearish":
                    reason = f"VWAP Short Reversion + Bearish Flow"
                    PositionTracker.add_position(ticker, "sell_to_open", price, reason)
                    await send_signal(ticker, "sell_to_open", reason, price, session)

        # === EXIT LOGIC ===
        else:
            entry_action = pos["action"]
            entry_price = float(pos["entry_price"])

            # Time-based exit or profit target
            if current_time >= datetime.strptime("15:50", "%H:%M").time():
                reason = "EOD Flatten"
                if "buy_to_open" in entry_action:
                    await send_signal(ticker, "sell_to_close", reason, price, session)
                else:
                    await send_signal(ticker, "buy_to_close", reason, price, session)
                PositionTracker.close_position(
                    ticker,
                    "sell_to_close" if "buy" in entry_action else "buy_to_close",
                    price,
                    reason,
                )

    except Exception as e:
        logger.error(f"Strategy error {ticker}: {e}")
