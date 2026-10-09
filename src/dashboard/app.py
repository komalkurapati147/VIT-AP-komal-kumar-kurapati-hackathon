"""Streamlit dashboard:  streamlit run dashboard/app.py   (run from repo root)"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
from risk_engine.engine import RiskEngine, write_jsonl
from risk_engine.ingest import JsonlSource
from risk_engine.config import UNIVERSE
from modules.rebalancer import run_rebalance
from modules.stress_test import SCENARIOS, run_stress, scan_signals

st.set_page_config(page_title="AI/NLP Risk Engine", layout="wide")
st.title("AI/NLP Risk Engine - Tactical Rebalancer & Event Stress Tester")

@st.cache_data
def load_signals():
    p = "output/signals.jsonl"
    if not os.path.exists(p):
        write_jsonl(RiskEngine([JsonlSource("data/sample_news.jsonl"), JsonlSource("data/sample_social.jsonl")]).run(), p)
    return [json.loads(l) for l in open(p, encoding="utf-8")]

signals = load_signals()
portfolio = pd.read_csv("data/sample_portfolio.csv")
sdf = pd.DataFrame(signals)

t0, t1, t2 = st.tabs(["Signal feed", "Module A: Rebalancer", "Module B: Stress test"])

with t0:
    c = st.columns(4)
    c[0].metric("Signals", len(sdf)); c[1].metric("Avg sentiment", f"{sdf.sentiment_score.mean():+.2f}")
    c[2].metric("High impact (>7)", int((sdf.impact_score > 7).sum())); c[3].metric("Sources", sdf.source.nunique())
    st.plotly_chart(px.histogram(sdf, x="event_type", color="sentiment_label", title="Events by type & sentiment",
                    color_discrete_map={"positive": "#2a9d8f", "neutral": "#999", "negative": "#e76f51"}), width="stretch")
    st.dataframe(sdf[["timestamp", "source", "entity", "sentiment_score", "event_type", "impact_score", "text"]],
                 width="stretch", hide_index=True)

with t1:
    st.sidebar.header("Rebalancer parameters")
    n = st.sidebar.slider("Index size", 10, 20, 15)
    hl = st.sidebar.slider("Sentiment half-life (min)", 15, 240, 90)
    k = st.sidebar.slider("Tilt strength k", 0.2, 3.0, 1.5)
    wmax = st.sidebar.slider("Max weight", 0.08, 0.25, 0.12)
    w, turn = run_rebalance(signals, UNIVERSE[:n], halflife_min=hl, k=k, w_max=wmax, w_min=0.01)
    long = w.reset_index().melt(id_vars="index", var_name="Ticker", value_name="Weight").rename(columns={"index": "Time"})
    st.plotly_chart(px.area(long, x="Time", y="Weight", color="Ticker", title="Index weights over time"), width="stretch")
    d = (w.iloc[-1] - w.iloc[0]).sort_values()
    st.plotly_chart(px.bar(d, title="Weight change: start -> end", labels={"value": "Δ weight", "index": ""}), width="stretch")
    st.caption(f"Average turnover per step: {turn.turnover.mean():.2%} | cumulative cost: {turn.cost_bps.sum():.2f} bps")

with t2:
    thr = st.slider("Trigger threshold (impact >)", 4.0, 9.0, 7.0, 0.5)
    trig = scan_signals(portfolio, signals, thr)
    st.write(f"{len(trig)} adverse high-impact signals triggered a stress test.")
    if trig:
        st.dataframe(pd.DataFrame(trig)[["timestamp", "event_type", "impact", "scale", "pnl", "pnl_pct", "text"]],
                     width="stretch", hide_index=True)
    mode = st.radio("Scenario", ["Worst triggered event", "Manual"], horizontal=True)
    if mode == "Manual":
        ev = st.selectbox("Event type", list(SCENARIOS)); imp = st.slider("Impact", 1.0, 10.0, 8.0)
    elif trig:
        worst = min(trig, key=lambda r: r["pnl"]); ev, imp = worst["event_type"], worst["impact"]
    else:
        ev, imp = "Geopolitical", 8.0
    res, summ = run_stress(portfolio, ev, imp)
    c = st.columns(3)
    c[0].metric("Value before", f"${summ['value_before']/1e6:,.1f}M")
    c[1].metric("Value after", f"${summ['value_after']/1e6:,.1f}M", f"{summ['pnl']/1e6:,.2f}M")
    c[2].metric("P&L %", f"{summ['pnl_pct']:.2f}%")
    g = res.groupby("asset_class")[["market_value", "stressed_value"]].sum().reset_index()
    fig = go.Figure([go.Bar(name="Before", x=g.asset_class, y=g.market_value, marker_color="#457b9d"),
                     go.Bar(name="After", x=g.asset_class, y=g.stressed_value, marker_color="#e63946")])
    fig.update_layout(barmode="group", title=f"{ev} (impact {imp}) - value by asset class")
    st.plotly_chart(fig, width="stretch")
    by_sec = res.groupby("sector").pnl.sum().sort_values()
    st.plotly_chart(px.bar(by_sec, title="P&L by sector", labels={"value": "P&L", "index": ""}), width="stretch")
    st.subheader("Top 10 loss contributors")
    st.dataframe(res.nsmallest(10, "pnl")[["position_id", "asset_class", "counterparty", "sector", "rating", "market_value", "pnl"]],
                 hide_index=True, width="stretch")
