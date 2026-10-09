import json, numpy as np, pandas as pd, pytest
from risk_engine import nlp
from risk_engine.engine import RiskEngine
from modules.rebalancer import run_rebalance, tilt_weights
from modules.stress_test import run_stress, should_trigger, SCENARIOS

def test_sentiment_direction():
    assert nlp.sentiment("Nvidia beats estimates, record profit") > 0.3
    assert nlp.sentiment("Company files for bankruptcy after default") < -0.3
    assert nlp.sentiment("Results were not strong") < 0          # negation
    assert -1 <= nlp.sentiment("crash crash crash plunge collapse " * 5) <= 1

@pytest.mark.parametrize("text,event", [
    ("Sanctions and military tensions escalate", "Geopolitical"),
    ("Fed hikes rates as inflation surges", "Macroeconomic"),
    ("Rating agency downgrade after loan default", "Credit Event"),
    ("Firm to acquire rival in all-cash deal", "Merger/Acquisition"),
    ("Company unveils new chip", "Product Launch"),
    ("Hospital group lunch menu", "Other")])
def test_event_classification(text, event):
    assert nlp.classify_event(text)[0] == event

def test_entities_and_dedupe():
    assert nlp.link_entities("$TSLA and Goldman Sachs") == ["GS", "TSLA"] or set(nlp.link_entities("$TSLA and Goldman Sachs")) == {"GS", "TSLA"}
    assert nlp.link_entities("Oil prices rise") == ["MARKET"]
    e = RiskEngine([]); d = {"id": "1", "ts": "2026-01-01T00:00:00+00:00", "source": "social", "text": "Tesla recall", "engagement": 5}
    assert len(e.analyze(d)) == 1 and e.analyze(d) == []

def test_signal_schema_and_ranges():
    s = RiskEngine([]).analyze({"id": "x", "ts": "t", "source": "news", "text": "Boeing files for chapter 11", "engagement": 0})[0]
    assert {"sentiment_score", "event_type", "impact_score", "entity"} <= set(s)
    assert -1 <= s["sentiment_score"] <= 1 and 1 <= s["impact_score"] <= 10

def test_weights_constraints():
    w = tilt_weights(np.array([5, -5] + [0] * 8, float), np.full(10, .1), k=2, w_min=.03, w_max=.15)
    assert abs(w.sum() - 1) < 1e-9 and w.min() >= .03 - 1e-9 and w.max() <= .15 + 1e-9

def test_rebalance_responds_to_sentiment():
    sig = [json.loads(l) for l in open("output/signals.jsonl", encoding="utf-8")]
    w, _ = run_rebalance(sig, ["NVDA", "BA", "AAPL", "MSFT", "KO", "JPM", "XOM", "WMT", "DIS", "PFE"])
    assert w.iloc[-1].sum() == pytest.approx(1)
    assert w["NVDA"].iloc[-1] > 0.1 and w["BA"].iloc[-1] < 0.1

def test_stress_monotonic_and_trigger():
    p = pd.read_csv("data/sample_portfolio.csv")
    _, lo = run_stress(p, "Geopolitical", 7); _, hi = run_stress(p, "Geopolitical", 10)
    assert hi["pnl"] < lo["pnl"] < 0
    assert should_trigger({"impact_score": 8, "sentiment_score": -.5, "event_type": "Geopolitical"})
    assert not should_trigger({"impact_score": 8, "sentiment_score": .5, "event_type": "Geopolitical"})
    assert not should_trigger({"impact_score": 6, "sentiment_score": -.5, "event_type": "Geopolitical"})
