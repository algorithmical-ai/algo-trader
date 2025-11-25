from datetime import time

from app.src.config.settings import settings
from app.src.core.signaler import send_signal
from app.src.data.unusual_whales import get_flow_signal
from app.src.indicators.technical import (calculate_rvol, calculate_vwap,
                                          get_opening_range, is_downtrend,
                                          is_uptrend)
from app.src.position_tracker.redis_tracker import PositionTracker
from app.src.utils.helpers import now_ny
from app.src.utils.logger import logger


async def evaluate_ticker(ticker: str, df_1m, df_daily, session):
    try:
        if (
            ticker not in df_1m.index.get_level_values(0)
            or df_1m.xs(ticker, level=0).empty
        ):
            return
        df_1m_t = df_1m.xs(ticker, level=0)
        if ticker in df_daily.index.get_level_values(0):
            df_daily_t = df_daily.xs(ticker, level=0)
        else:
            return

        if len(df_daily_t) < 200:
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

        orb_high, orb_low = get_opening_range(today_df)
        if orb_high is None:
            return

        vwap_val = calculate_vwap(today_df)
        flow = await get_flow_signal(ticker, session)

        pos = PositionTracker.get_position(ticker)
        current_time = now_ny().time()
        orb_end_time = time.fromisoformat(settings.ORB_PHASE_END)

        # Entry Logic
        if not pos:
            if current_time <= orb_end_time:
                # ORB Long
                if (
                    price > orb_high
                    and price > vwap_val
                    and is_uptrend(df_daily_t)
                    and flow == "bullish"
                ):
                    reason = f"ORB Breakout + Bullish Flow + RVOL {rvol:.1f}x"
                    PositionTracker.add_position(ticker, "buy_to_open", price, reason)
                    await send_signal(ticker, "buy_to_open", reason, price, session)
                    return
                # ORB Short
                if (
                    price < orb_low
                    and price < vwap_val
                    and is_downtrend(df_daily_t)
                    and flow == "bearish"
                ):
                    reason = f"ORB Breakdown + Bearish Flow + RVOL {rvol:.1f}x"
                    PositionTracker.add_position(ticker, "sell_to_open", price, reason)
                    await send_signal(ticker, "sell_to_open", reason, price, session)
                    return
            else:
                # VWAP Long Reversion
                if price < vwap_val and is_uptrend(df_daily_t) and flow == "bullish":
                    reason = f"VWAP Dip Buy + Bullish Flow + RVOL {rvol:.1f}x"
                    PositionTracker.add_position(ticker, "buy_to_open", price, reason)
                    await send_signal(ticker, "buy_to_open", reason, price, session)
                    return
                # VWAP Short Reversion
                if price > vwap_val and is_downtrend(df_daily_t) and flow == "bearish":
                    reason = f"VWAP Rally Fade + Bearish Flow + RVOL {rvol:.1f}x"
                    PositionTracker.add_position(ticker, "sell_to_open", price, reason)
                    await send_signal(ticker, "sell_to_open", reason, price, session)
                    return

        # Exit Logic
        if pos:
            entry_action = pos["action"]
            entry_price = pos["entry_price"]
            pnl_pct = (
                ((price - entry_price) / entry_price) * 100
                if "buy_to_open" in entry_action
                else ((entry_price - price) / entry_price) * 100
            )

            # Profit Target: 2% or EOD
            if (
                (pnl_pct >= 2.0 and "buy_to_open" in entry_action)
                or (pnl_pct <= -2.0 and "sell_to_open" in entry_action)
                or current_time >= time.fromisoformat(settings.TRADING_END)
            ):
                reason = f"Target Hit/EOD | PnL: {pnl_pct:+.2f}%"
                exit_action = (
                    "sell_to_close" if "buy_to_open" in entry_action else "buy_to_close"
                )
                await send_signal(ticker, exit_action, reason, price, session)
                PositionTracker.close_position(ticker, exit_action, price, reason)

    except Exception as e:
        logger.error(f"Evaluation error for {ticker}: {e}")
