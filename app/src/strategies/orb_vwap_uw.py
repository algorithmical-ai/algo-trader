from datetime import time

from app.src.config.settings import settings
from app.src.core.signaler import send_signal
from app.src.data.unusual_whales import (
    get_congress_trades,
    get_dark_pool,
    get_flow_signal,
    get_iv_rank,
    get_screener_tickers,
)
from app.src.indicators.technical import (
    calculate_rvol,
    calculate_vwap,
    get_opening_range,
    is_downtrend,
    is_uptrend,
)
from app.src.position_tracker.dynamodb_tracker import PositionTracker
from app.src.utils.helpers import get_dynamic_min_rvol, now_ny
from app.src.utils.logger import logger

WATCHLIST = settings.WATCHLIST.copy()


async def refresh_watchlist(session):
    """New: Daily refresh with screener."""
    tickers = await get_screener_tickers(session)
    WATCHLIST.clear()
    WATCHLIST.extend(tickers)
    logger.info(f"Watchlist refreshed: {len(WATCHLIST)} tickers")


def _normalize_signal(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _safe_float(value) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        logger.warning(f"Unable to coerce value '{value}' to float; defaulting to 0.0")
        return 0.0


def _log_skip(ticker: str, reason: str, **context):
    extra = ""
    if context:
        kv = ", ".join(f"{k}={v}" for k, v in context.items())
        extra = f" | {kv}"
    logger.info(f"NO TRADE {ticker}: {reason}{extra}")


async def evaluate_ticker(ticker: str, df_1m, df_daily, session):
    try:
        if ticker not in df_1m.index.get_level_values(0):
            _log_skip(ticker, "No intraday data returned")
            return
        df_1m_t = df_1m.xs(ticker, level=0)
        df_daily_t = (
            df_daily.xs(ticker, level=0)
            if ticker in df_daily.index.get_level_values(0)
            else None
        )
        if df_daily_t is None or df_daily_t.empty or len(df_daily_t) < 200:
            _log_skip(
                ticker,
                "Insufficient daily history",
                bars=len(df_daily_t) if df_daily_t is not None else 0,
            )
            return

        today_df = df_1m_t[df_1m_t.index.date == now_ny().date()]
        if len(today_df) < 10:
            _log_skip(ticker, "Not enough intraday bars for today", bars=len(today_df))
            return

        price = today_df["close"].iloc[-1]
        if price < settings.MIN_PRICE:
            _log_skip(
                ticker,
                "Price below MIN_PRICE",
                price=f"{price:.2f}",
                min_price=settings.MIN_PRICE,
            )
            return

        rvol = calculate_rvol(df_1m_t, df_daily_t)
        min_rvol = get_dynamic_min_rvol()
        if rvol < min_rvol:
            _log_skip(ticker, "RVOL below threshold", rvol=f"{rvol:.2f}", min_rvol=f"{min_rvol:.2f}")
            return

        orb_high, orb_low = get_opening_range(today_df)
        if orb_high is None or orb_low is None:
            _log_skip(ticker, "Opening range unavailable")
            return

        vwap_val = calculate_vwap(today_df)

        # MAX UW USAGE
        flow = _normalize_signal(await get_flow_signal(ticker, session))
        congress = _normalize_signal(await get_congress_trades(ticker, session))
        dark = _normalize_signal(await get_dark_pool(ticker, session))
        high_iv = _safe_float(await get_iv_rank(ticker, session))

        pos = PositionTracker.get_position(ticker)
        current_time = now_ny().time()
        orb_end_time = time.fromisoformat(settings.ORB_PHASE_END)

        # ENTRY: ORB + VWAP + FLOW + CONGRESS + DARK + IV
        if not pos and high_iv >= settings.MIN_IV_RANK:
            if current_time <= orb_end_time:
                if (
                    price > orb_high
                    and price > vwap_val
                    and is_uptrend(df_daily_t)
                    and flow == "bullish"
                    and "bullish" in congress
                    and "bullish" in dark
                ):
                    reason = f"ORB Breakout + Bullish Flow + Congress Buy + Dark Pool + High IV {rvol:.1f}x"
                    PositionTracker.add_position(ticker, "buy_to_open", price, reason)
                    await send_signal(ticker, "buy_to_open", reason, price, session, indicator=settings.INDICATOR_NAME)
                    return
                if (
                    price < orb_low
                    and price < vwap_val
                    and is_downtrend(df_daily_t)
                    and flow == "bearish"
                ):
                    reason = f"ORB Breakdown + Bearish Flow + RVOL {rvol:.1f}x"
                    PositionTracker.add_position(ticker, "sell_to_open", price, reason)
                    await send_signal(ticker, "sell_to_open", reason, price, session, indicator=settings.INDICATOR_NAME)
                    return
            else:
                if (
                    price < vwap_val
                    and is_uptrend(df_daily_t)
                    and flow == "bullish"
                    and "bullish" in congress
                ):
                    reason = "VWAP Dip + Bullish Flow + Congress + High IV"
                    PositionTracker.add_position(ticker, "buy_to_open", price, reason)
                    await send_signal(ticker, "buy_to_open", reason, price, session, indicator=settings.INDICATOR_NAME)
                    return
                if price > vwap_val and is_downtrend(df_daily_t) and flow == "bearish":
                    reason = "VWAP Rally Fade + Bearish Flow"
                    PositionTracker.add_position(ticker, "sell_to_open", price, reason)
                    await send_signal(ticker, "sell_to_open", reason, price, session, indicator=settings.INDICATOR_NAME)
                    return
        elif not pos:
            _log_skip(
                ticker,
                "IV rank filter failed",
                iv_rank=f"{high_iv:.1f}",
                required=settings.MIN_IV_RANK,
            )

        # EXIT: PnL + unusual put/call flow
        if pos:
            entry_action = pos["action"]
            entry_price = pos["entry_price"]
            pnl_pct = (
                ((price - entry_price) / entry_price) * 100
                if "buy_to_open" in entry_action
                else ((entry_price - price) / entry_price) * 100
            )

            exit_flow = _normalize_signal(await get_flow_signal(ticker, session))
            if (
                (
                    pnl_pct >= 2.0
                    and "buy_to_open" in entry_action
                    and exit_flow == "bearish"
                )
                or (
                    pnl_pct <= -2.0
                    and "sell_to_open" in entry_action
                    and exit_flow == "bullish"
                )
                or current_time >= time.fromisoformat(settings.TRADING_END)
            ):
                reason = f"Target Hit + Flow Exit | PnL: {pnl_pct:+.2f}%"
                exit_action = (
                    "sell_to_close" if "buy_to_open" in entry_action else "buy_to_close"
                )
                await send_signal(ticker, exit_action, reason, price, session, indicator=settings.INDICATOR_NAME)
                PositionTracker.close_position(ticker, exit_action, price, reason)

    except Exception:
        logger.exception(f"Strategy error {ticker}")
