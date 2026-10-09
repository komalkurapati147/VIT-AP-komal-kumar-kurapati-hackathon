"""NLP components: entity linking, sentiment, event classification, impact scoring.

Default backend is a transparent finance-lexicon model (no downloads, deterministic).
Set SENTIMENT_BACKEND=finbert to use ProsusAI/finbert via transformers if installed.
"""
import math, os, re
from . import config as C

_TOKEN = re.compile(r"[a-z][a-z'\-&]*")
_ENTITY_PATTERNS = {}
for t, (_, aliases, _) in C.ENTITIES.items():
    alias_rx = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
    _ENTITY_PATTERNS[t] = (re.compile(rf"(?<![A-Za-z])({alias_rx})(?![A-Za-z])", re.I),
                           re.compile(rf"(?:\$|\b){t}\b"))  # tickers: case-sensitive


def link_entities(text: str):
    found = []
    for t, (name_rx, tick_rx) in _ENTITY_PATTERNS.items():
        if name_rx.search(text) or tick_rx.search(text):
            found.append(t)
    return found or [C.MARKET]


def _lexicon_sentiment(text: str) -> float:
    low = text.lower()
    raw = 0.0
    for ph, w in C.PHRASES.items():
        if ph in low:
            raw += w
            low = low.replace(ph, " ")
    toks = _TOKEN.findall(low)
    for i, tok in enumerate(toks):
        w = C.POS.get(tok, 0.0) - C.NEG.get(tok, 0.0)
        if w and any(p in C.NEGATORS for p in toks[max(0, i - 3):i]):
            w = -0.7 * w  # negation flips and dampens
        raw += w
    for e, w in C.EMOJI.items():
        raw += w * text.count(e)
    return raw / (abs(raw) + 2.5)  # smooth squash into (-1, 1)


_finbert = None
def _finbert_sentiment(text: str) -> float:
    global _finbert
    if _finbert is None:
        from transformers import pipeline
        _finbert = pipeline("text-classification", model="ProsusAI/finbert", top_k=None)
    out = {d["label"].lower(): d["score"] for d in _finbert(text[:512])[0]}
    return out.get("positive", 0) - out.get("negative", 0)


def sentiment(text: str) -> float:
    lex = _lexicon_sentiment(text)
    if os.getenv("SENTIMENT_BACKEND") == "finbert":
        try:
            return round(0.7 * _finbert_sentiment(text) + 0.3 * lex, 3)
        except Exception:
            pass
    return round(lex, 3)


def sentiment_label(s: float) -> str:
    return "positive" if s > 0.15 else "negative" if s < -0.15 else "neutral"


_EVENT_RX = {e: [(re.compile(p, re.I), w) for p, w in rules] for e, rules in C.EVENT_RULES.items()}
def classify_event(text: str):
    scores = {e: sum(w * len(rx.findall(text)) for rx, w in rules) for e, rules in _EVENT_RX.items()}
    best = max(scores, key=scores.get)
    top, total = scores[best], sum(scores.values())
    if top < 2:
        return "Other", 0.3
    return best, round(min(0.99, 0.35 + 0.65 * top / (total + 1e-9) * min(1, top / 4)), 2)


def intensity(text: str) -> float:
    toks = set(_TOKEN.findall(text.lower()))
    hits = len(toks & C.INTENSIFIERS) + min(text.count("!"), 2) * 0.5 + (0.5 if text.isupper() else 0)
    return round(min(1.0, hits / 3), 2)


def credibility(source: str, engagement: int = 0) -> float:
    base = C.SOURCE_CREDIBILITY.get(source, 0.5)
    if source == "social":  # engagement-adjusted: 0.3 .. 0.7
        base = 0.3 + 0.4 * min(1.0, math.log10(1 + max(engagement, 0)) / 4)
    return round(base, 2)


def impact_score(event: str, sent: float, inten: float, cred: float) -> float:
    """Transparent 1-10 severity: event prior + sentiment magnitude + intensity + source trust."""
    raw = 0.55 * C.BASE_SEVERITY[event] + 3.0 * abs(sent) + 2.0 * inten + 1.5 * cred
    return round(max(1.0, min(10.0, raw)), 1)
