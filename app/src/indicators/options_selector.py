import math
from datetime import datetime
from typing import Dict, List, Optional


class WheelOptionsSelector:
    @staticmethod
    def select_best_put(
        chain: list[dict], spot_price: float, iv_rank: float
    ) -> Optional[dict]:
        if iv_rank < 70:
            return None

        candidates = []
        for c in chain:
            if c.get("option_type") != "put":
                continue
            strike = float(c["strike_price"])
            dte = (
                datetime.fromisoformat(c["expiration_date"].split("T")[0])
                - datetime.now()
            ).days
            if not (30 <= dte <= 45):
                continue
            delta_val = c.get("delta")
            if delta_val is None:
                # If delta not available, skip delta filtering but still consider the contract
                delta = 0.20  # Use middle of range as default
            else:
                delta = abs(float(delta_val))
                if not (0.15 <= delta <= 0.30):
                    continue
            if strike >= spot_price:
                continue
            distance = (spot_price - strike) / spot_price
            if not (0.05 <= distance <= 0.12):
                continue
            premium = float(c["bid"])
            score = premium * 100 + distance * 10
            candidates.append(
                {
                    "contract": c["symbol"],
                    "strike": strike,
                    "premium": premium,
                    "dte": dte,
                    "delta": round(delta, 3),
                    "distance_pct": round(distance * 100, 2),
                    "score": score,
                }
            )
        return max(candidates, key=lambda x: x["score"]) if candidates else None

    @staticmethod
    def select_best_call(chain: List[dict], spot_price: float) -> Optional[Dict]:
        candidates = []
        for c in chain:
            if c.get("option_type") != "call":
                continue
            strike = float(c["strike_price"])
            dte = (
                datetime.fromisoformat(c["expiration_date"].split("T")[0])
                - datetime.now()
            ).days
            if not (21 <= dte <= 45):
                continue
            delta_val = c.get("delta")
            if delta_val is None:
                # If delta not available, skip delta filtering but still consider the contract
                delta = 0.35  # Use middle of range as default
            else:
                delta = float(delta_val)
                if not (0.25 <= delta <= 0.45):
                    continue
            if strike <= spot_price:
                continue
            premium = float(c["bid"])
            score = premium * 100
            candidates.append(
                {
                    "contract": c["symbol"],
                    "strike": strike,
                    "premium": premium,
                    "dte": dte,
                    "delta": round(delta, 3),
                    "score": score,
                }
            )
        return max(candidates, key=lambda x: x["score"]) if candidates else None
