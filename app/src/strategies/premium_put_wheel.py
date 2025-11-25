# app/src/strategies/premium_put_wheel.py
from app.src.core.signaler import send_signal
from app.src.indicators.options_selector import WheelOptionsSelector


async def evaluate_premium_put(
    ticker: str, spot_price: float, option_chain: list, iv_rank: float, session
):
    best_put = WheelOptionsSelector.select_best_put(option_chain, spot_price, iv_rank)

    if best_put:
        reason = (
            f"Premium Put Wheel | Δ{best_put['delta']:.2f} | "
            f"{best_put['distance_pct']}% OTM | IVR {iv_rank:.0f} | "
            f"Credit ${best_put['premium']:.2f}"
        )

        await send_signal(
            ticker,
            "sell_to_open_put",
            reason,
            best_put["premium"],
            session,
            extra={"option_contract": best_put["symbol"]},  # e.g., AAPL250617P00250000
            indicator="PremiumPutWheel_Pro",
        )
