"""Generates docs/architecture.png and result charts from real engine output (run: python main.py ... or python src/make_docs_assets.py)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd
from modules.rebalancer import run_rebalance
from modules.stress_test import scan_signals, run_stress

os.makedirs("docs", exist_ok=True)
sig = [json.loads(l) for l in open("output/signals.jsonl", encoding="utf-8")]
port = pd.read_csv("data/sample_portfolio.csv")

# ---------- architecture ----------
fig, ax = plt.subplots(figsize=(16, 8), dpi=130); ax.set_xlim(0, 16); ax.set_ylim(0, 8); ax.axis("off")
def box(x, y, w, h, t, c, fs=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15", fc=c, ec="none"))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", color="white", fontsize=fs, fontweight="bold", linespacing=1.4)
def arrow(x1, y1, x2, y2): ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", lw=2, color="#334155"))
box(.3, 5.0, 3.2, 1.3, "Financial news\nRSS / NewsAPI / JSONL", "#0f766e"); box(.3, 2.9, 3.2, 1.3, "Social posts\nReddit / X-style JSONL", "#0f766e")
box(4.3, 3.2, 3.3, 2.6, "1. INGEST + CLEAN\nURL / retweet strip\nnear-duplicate drop\nsource credibility", "#1e3a8a")
box(8.4, 3.2, 3.8, 2.6, "2. NLP RISK ENGINE\nentity linking (20 stocks)\nsentiment  [-1, 1]\nevent class (8 types)\nimpact score  [1-10]", "#7c2d12")
box(12.9, 3.5, 2.9, 2.0, "3. STRUCTURED SIGNALS\nsignals.jsonl\nREST API", "#4c1d95")
box(8.4, 1.5, 3.8, 1.1, "MODULE A: sentiment-tilted\nindex rebalancer", "#b45309"); box(12.4, 1.5, 3.4, 1.1, "MODULE B: event-driven\nstress tester", "#b91c1c")
box(8.4, 0.1, 7.4, 0.9, "Streamlit dashboard: feed | weights over time | stress P&L", "#0369a1", 10)
for a_ in [(3.5, 5.6, 4.3, 5.0), (3.5, 3.5, 4.3, 4.0), (7.6, 4.5, 8.4, 4.5), (12.2, 4.5, 12.9, 4.5),
           (13.3, 3.5, 12.0, 2.6), (14.6, 3.5, 14.2, 2.6), (10.3, 1.5, 10.3, 1.0), (14.1, 1.5, 14.1, 1.0)]: arrow(*a_)
ax.set_title("System architecture & data flow", fontsize=16, fontweight="bold", loc="left")
plt.savefig("docs/architecture.png", bbox_inches="tight"); plt.close()

# ---------- Module A chart ----------
w, turn = run_rebalance(sig)
fig, ax = plt.subplots(figsize=(11, 5), dpi=130)
(w * 100).plot.area(ax=ax, stacked=True, colormap="tab20", linewidth=0)
ax.set_ylabel("Weight (%)"); ax.set_xlabel(""); ax.set_title("Module A: index weights over time (15 stocks)", loc="left", fontweight="bold")
ax.legend(ncol=5, fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.12)); ax.set_ylim(0, 100)
plt.savefig("docs/results_rebalancer.png", bbox_inches="tight"); plt.close()
d = ((w.iloc[-1] - w.iloc[0]) * 100).sort_values()
fig, ax = plt.subplots(figsize=(7, 5), dpi=130)
ax.barh(d.index, d.values, color=["#dc2626" if v < 0 else "#0f766e" for v in d.values]); ax.set_xlabel("Weight change (pp), start to end")
ax.set_title("Who gained / lost weight", loc="left", fontweight="bold"); plt.savefig("docs/results_weight_change.png", bbox_inches="tight"); plt.close()

# ---------- Module B chart ----------
rows = []
for ev, imp in [("Geopolitical", 8.5), ("Credit Event", 8.5), ("Macroeconomic", 8.5), ("Cyber/Operational", 8.5), ("Regulatory/Legal", 8.5)]:
    _, s = run_stress(port, ev, imp); rows.append((ev, s["pnl_pct"], s["pnl"] / 1e6))
res, summ = run_stress(port, "Credit Event", 8.5)
g = res.groupby("asset_class")[["market_value", "stressed_value"]].sum() / 1e6
fig, axs = plt.subplots(1, 2, figsize=(13, 5), dpi=130)
g.plot.bar(ax=axs[0], color=["#2563eb", "#dc2626"], rot=30); axs[0].set_title("Credit Event (impact 8.5): value by asset class ($M)", loc="left", fontweight="bold"); axs[0].legend(["Before", "After"])
axs[1].bar([r[0] for r in rows], [r[1] for r in rows], color="#dc2626"); axs[1].set_ylabel("P&L % of book"); axs[1].tick_params(axis="x", rotation=30)
axs[1].set_title("Scenario P&L % at impact 8.5", loc="left", fontweight="bold")
plt.tight_layout(); plt.savefig("docs/results_stress.png", bbox_inches="tight"); plt.close()

trig = scan_signals(port, sig)
stats = dict(n_signals=len(sig), n_docs=48, high_impact=sum(s["impact_score"] > 7 for s in sig),
             triggers=len(trig), worst=min(trig, key=lambda r: r["pnl"]) if trig else None,
             book=float(port.market_value.sum()), scen=rows, avg_turnover=float(turn.turnover.mean()),
             top_up=d.tail(3).round(2).to_dict(), top_down=d.head(3).round(2).to_dict())
json.dump(stats, open("docs/stats.json", "w"), indent=1, default=str)
print(json.dumps(stats, indent=1, default=str))
