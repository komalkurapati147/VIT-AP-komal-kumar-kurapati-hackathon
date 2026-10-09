"""Simple REST API:  uvicorn risk_engine.api:app --reload"""
import json, os
from fastapi import FastAPI
from pydantic import BaseModel
from .engine import RiskEngine

app = FastAPI(title="Risk Signal API")
PATH = os.getenv("SIGNALS_PATH", "output/signals.jsonl")


class Item(BaseModel):
    text: str
    source: str = "news"
    engagement: int = 0


def _load():
    return [json.loads(l) for l in open(PATH, encoding="utf-8")] if os.path.exists(PATH) else []


@app.get("/signals")
def signals(entity: str | None = None, min_impact: float = 0, limit: int = 100):
    rows = [s for s in _load() if s["impact_score"] >= min_impact and (not entity or s["entity"] == entity.upper())]
    return rows[-limit:]


@app.post("/analyze")
def analyze(item: Item):
    doc = {"id": "adhoc", "ts": "now", "source": item.source, "text": item.text, "engagement": item.engagement}
    return RiskEngine([]).analyze(doc)
