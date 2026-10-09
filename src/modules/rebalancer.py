"""Module A - Tactical sentiment-tilted index rebalancer.

Per-ticker sentiment state s_i decays exponentially (half-life H) and is bumped by each new signal:
    s_i += sentiment * (impact/10) * credibility          (market-wide signals: x0.3 to every stock)
Target weight:  w_i  proportional to  w0_i * exp(k * tanh(s_i))
subject to per-name bounds [w_min, w_max] (iterative clip + renormalise).
"""
import numpy as np, pandas as pd
from risk_engine.config import MARKET, UNIVERSE


def tilt_weights(s: np.ndarray, w0: np.ndarray, k=1.5, w_min=0.02, w_max=0.12):
    """Exponential tilt followed by exact bounded projection (water-filling): sums to 1 within [w_min, w_max]."""
    n = len(s)
    w_min, w_max = min(w_min, 1 / n), max(w_max, 1 / n)   # keep the problem feasible for small universes
    w = w0 * np.exp(k * np.tanh(s))
    w /= w.sum()
    fixed = np.zeros(n, bool)
    for _ in range(n + 1):
        w = np.where(fixed, w, w)  # no-op, keeps shape
        free = ~fixed
        budget = 1 - w[fixed].sum()
        w[free] = w[free] / w[free].sum() * budget
        over, under = free & (w > w_max + 1e-12), free & (w < w_min - 1e-12)
        if not over.any() and not under.any():
            break
        w[over], w[under] = w_max, w_min
        fixed |= over | under
    return w


def run_rebalance(signals, universe=None, halflife_min=90, k=1.5, w_min=0.02, w_max=0.12,
                  step_min=15, market_beta=0.3, cost_bps=5):
    """signals: list[dict] from the engine. Returns (weights_df, turnover_df)."""
    universe = universe or UNIVERSE[:15]
    df = pd.DataFrame(signals)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")
    idx = list(universe)
    n = len(idx)
    w0 = np.full(n, 1 / n)
    s = np.zeros(n)
    times = pd.date_range(df["timestamp"].min().floor(f"{step_min}min"),
                          df["timestamp"].max().ceil(f"{step_min}min"), freq=f"{step_min}min")
    rows, turn, prev_w, ptr = [], [], w0, 0
    recs = df.to_dict("records")
    for t in times:
        s *= 0.5 ** (step_min / halflife_min)
        while ptr < len(recs) and recs[ptr]["timestamp"] <= t:
            r = recs[ptr]; ptr += 1
            bump = r["sentiment_score"] * r["impact_score"] / 10 * r["credibility"]
            if r["entity"] == MARKET: s += market_beta * bump
            elif r["entity"] in idx: s[idx.index(r["entity"])] += bump
        w = tilt_weights(s, w0, k, w_min, w_max)
        rows.append(pd.Series(w, index=idx, name=t))
        turn.append({"timestamp": t, "turnover": 0.5 * np.abs(w - prev_w).sum(),
                     "cost_bps": cost_bps * np.abs(w - prev_w).sum() * 1e4 / 1e4})
        prev_w = w
    return pd.DataFrame(rows), pd.DataFrame(turn).set_index("timestamp")
