"""RiskEngine: ingest -> clean/dedupe -> entity link -> NLP -> structured signals (JSONL / API)."""
import argparse, json, re
from . import nlp
from .ingest import JsonlSource, RssSource, NewsApiSource, RedditSource


def clean(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^RT @\w+:\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


class RiskEngine:
    def __init__(self, sources):
        self.sources = sources
        self._seen = set()

    def analyze(self, doc: dict):
        """Return one structured signal per company mentioned (or MARKET)."""
        text = clean(doc["text"])
        key = re.sub(r"\W+", "", text.lower())[:80]
        if not text or key in self._seen:   # drop empty and near-duplicate (retweet) items
            return []
        self._seen.add(key)
        s = nlp.sentiment(text)
        event, conf = nlp.classify_event(text)
        inten = nlp.intensity(text)
        cred = nlp.credibility(doc["source"], doc.get("engagement", 0))
        impact = nlp.impact_score(event, s, inten, cred)
        return [{
            "signal_id": f"{doc['id']}:{t}", "timestamp": doc["ts"], "source": doc["source"],
            "entity": t, "sentiment_score": s, "sentiment_label": nlp.sentiment_label(s),
            "event_type": event, "event_confidence": conf, "impact_score": impact,
            "credibility": cred, "text": text[:240],
        } for t in nlp.link_entities(text)]

    def run(self):
        out = []
        for src in self.sources:
            try:
                for doc in src.fetch():
                    out.extend(self.analyze(doc))
            except Exception as e:  # one failing feed must not stop the pipeline
                print(f"[warn] source {type(src).__name__} failed: {e}")
        return sorted(out, key=lambda x: x["timestamp"])


def write_jsonl(signals, path):
    with open(path, "w", encoding="utf-8") as f:
        for s in signals:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Run the AI/NLP Risk Engine")
    ap.add_argument("--live", action="store_true", help="use live RSS (+NewsAPI if key set) + Reddit")
    ap.add_argument("--out", default="output/signals.jsonl")
    a = ap.parse_args()
    if a.live:
        import os
        srcs = [RssSource(), RedditSource("stocks")]
        if os.getenv("NEWSAPI_KEY"): srcs.append(NewsApiSource())
    else:
        srcs = [JsonlSource("data/sample_news.jsonl"), JsonlSource("data/sample_social.jsonl")]
    sig = RiskEngine(srcs).run()
    write_jsonl(sig, a.out)
    print(f"wrote {len(sig)} signals -> {a.out}")


if __name__ == "__main__":
    main()
