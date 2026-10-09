"""Module B - Event-driven portfolio stress testing for a synthetic wholesale-banking book.

Trigger: signal with impact_score > threshold, adverse sentiment, and an event type that has a scenario.
Shocks scale with severity:  scale = clip(impact/7, 0.5, 2.0)  (impact 7 => 1.0x the base scenario).
"""
import numpy as np, pandas as pd

# Base shocks. equity: % move; rates_bps: parallel shift; spread_bps: IG credit-spread widening (HY gets x rating mult)
# fx_foreign: % change of foreign ccy vs USD; commodity: % move; pd_mult: PD multiplier
SCENARIOS = {
    "Geopolitical":      dict(equity=-.12, rates_bps=-30, spread_bps=90,  fx_foreign=-.04, commodity=.15, pd_mult=1.4,
                              sector_eq={"Energy": .6, "Industrials": 1.3, "Technology": 1.1}),
    "Macroeconomic":     dict(equity=-.08, rates_bps=75,  spread_bps=60,  fx_foreign=-.03, commodity=-.05, pd_mult=1.3,
                              sector_eq={"Financials": 1.2, "Technology": 1.3}),
    "Credit Event":      dict(equity=-.10, rates_bps=-15, spread_bps=150, fx_foreign=-.02, commodity=-.03, pd_mult=2.0,
                              sector_eq={"Financials": 1.5}),
    "Regulatory/Legal":  dict(equity=-.05, rates_bps=0,   spread_bps=30,  fx_foreign=0.0,  commodity=0.0, pd_mult=1.1,
                              sector_eq={"Technology": 1.5, "Financials": 1.2}),
    "Cyber/Operational": dict(equity=-.06, rates_bps=0,   spread_bps=40,  fx_foreign=-.01, commodity=0.0, pd_mult=1.15,
                              sector_eq={"Technology": 1.3, "Financials": 1.3}),
}
RATING_SPREAD_MULT = {"A": .7, "BBB": 1.0, "BB": 2.0, "B": 3.2}


def should_trigger(sig, threshold=7.0):
    return sig["impact_score"] > threshold and sig["sentiment_score"] <= -0.15 and sig["event_type"] in SCENARIOS


def revalue(pos: pd.Series, sc: dict, scale: float) -> float:
    """Return P&L for one position under the scaled scenario."""
    dy, ds = sc["rates_bps"] * scale / 1e4, sc["spread_bps"] * scale / 1e4
    ac, rm = pos.asset_class, RATING_SPREAD_MULT.get(pos.rating, 1.0)
    if ac == "Equity":
        return pos.market_value * pos.beta * sc["equity"] * scale * sc["sector_eq"].get(pos.sector, 1.0)
    if ac == "Bond":
        return pos.market_value * (-pos.duration * dy - pos.spread_duration * ds * rm)
    if ac == "Loan":  # floating-rate: spread repricing + expected-loss uplift
        dpd = pos.pd * (sc["pd_mult"] - 1) * scale * rm
        return pos.market_value * (-pos.spread_duration * ds * rm) - pos.notional * dpd * pos.lgd
    if ac == "IRS":   # direction +1 receive-fixed (gains when rates fall)
        return -pos.direction * pos.dv01 * sc["rates_bps"] * scale
    if ac == "FX_Forward":
        return pos.direction * pos.notional * sc["fx_foreign"] * scale if pos.currency != "USD" else 0.0
    if ac == "Commodity_Swap":
        return pos.direction * pos.notional * sc["commodity"] * scale
    return 0.0


def run_stress(portfolio: pd.DataFrame, event_type: str, impact: float):
    sc, scale = SCENARIOS[event_type], float(np.clip(impact / 7, 0.5, 2.0))
    out = portfolio.copy()
    out["pnl"] = out.apply(lambda r: revalue(r, sc, scale), axis=1)
    out["stressed_value"] = out["market_value"] + out["pnl"]
    before, after = out["market_value"].sum(), out["stressed_value"].sum()
    return out, {"event_type": event_type, "impact": impact, "scale": round(scale, 2),
                 "value_before": before, "value_after": after, "pnl": after - before,
                 "pnl_pct": (after - before) / before * 100}


def scan_signals(portfolio, signals, threshold=7.0):
    """Run a stress test for every triggering signal; returns list of result dicts."""
    res = []
    for s in signals:
        if should_trigger(s, threshold):
            _, summ = run_stress(portfolio, s["event_type"], s["impact_score"])
            res.append({**summ, "timestamp": s["timestamp"], "entity": s["entity"], "text": s["text"]})
    return res
