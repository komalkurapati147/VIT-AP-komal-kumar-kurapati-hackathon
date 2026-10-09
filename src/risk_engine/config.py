"""Static configuration: entity universe, event taxonomy, lexicons."""
import re

ENTITIES = {
    "AAPL": ("Apple", ["Apple", "iPhone"], "Technology"),
    "MSFT": ("Microsoft", ["Microsoft", "Azure"], "Technology"),
    "AMZN": ("Amazon", ["Amazon", "AWS"], "Consumer"),
    "GOOGL": ("Alphabet", ["Alphabet", "Google"], "Technology"),
    "META": ("Meta", ["Meta Platforms", "Meta", "Facebook"], "Technology"),
    "NVDA": ("Nvidia", ["Nvidia"], "Technology"),
    "TSLA": ("Tesla", ["Tesla"], "Consumer"),
    "JPM": ("JPMorgan", ["JPMorgan", "JP Morgan"], "Financials"),
    "BAC": ("Bank of America", ["Bank of America", "BofA"], "Financials"),
    "GS": ("Goldman Sachs", ["Goldman Sachs", "Goldman"], "Financials"),
    "XOM": ("Exxon Mobil", ["Exxon Mobil", "Exxon"], "Energy"),
    "CVX": ("Chevron", ["Chevron"], "Energy"),
    "JNJ": ("Johnson & Johnson", ["Johnson & Johnson", "J&J"], "Healthcare"),
    "PFE": ("Pfizer", ["Pfizer"], "Healthcare"),
    "WMT": ("Walmart", ["Walmart"], "Consumer"),
    "KO": ("Coca-Cola", ["Coca-Cola", "Coca Cola"], "Consumer"),
    "DIS": ("Disney", ["Disney"], "Communication"),
    "BA": ("Boeing", ["Boeing"], "Industrials"),
    "INTC": ("Intel", ["Intel"], "Technology"),
    "NFLX": ("Netflix", ["Netflix"], "Communication"),
}
UNIVERSE = list(ENTITIES)
MARKET = "MARKET"  # used when no company is mentioned (macro / geopolitical items)

# ---- Event taxonomy: regex -> weight. Highest summed weight wins. ----
EVENT_RULES = {
    "Geopolitical": [
        (r"\b(war|invasion|missile|sanctions?|embargo|ceasefire|military|conflict|tensions?)\b", 2),
        (r"\b(tariffs?|trade war|export controls?|strait|blockade|coup|nato|geopolitic\w*)\b", 2),
        (r"\b(opec|oil supply|shipping lanes?|border)\b", 1),
    ],
    "Macroeconomic": [
        (r"\b(inflation|cpi|gdp|recession|unemployment|jobs report|payrolls?|rate (hike|cut)s?)\b", 2),
        (r"\b(fed|federal reserve|ecb|central bank|interest rates?|yield curve|treasury yields?)\b", 2),
        (r"\b(consumer spending|pmi|stagflation|soft landing|monetary policy)\b", 1),
    ],
    "Credit Event": [
        (r"\b(default(s|ed)?|bankruptcy|chapter 11|insolvency|downgrad\w*|junk|restructuring)\b", 3),
        (r"\b(credit rating|debt load|covenant|bond selloff|liquidity crunch|bailout|write-?downs?)\b", 2),
        (r"\b(cds|credit spreads?|missed (a )?payment)\b", 2),
    ],
    "Merger/Acquisition": [
        (r"\b(acquir\w*|acquisition|merger|merge[sd]?|takeover|buyout|buy out|divest\w*|spin-?off)\b", 3),
        (r"\b(to buy|bid for|deal valued|all-cash deal|antitrust review)\b", 2),
    ],
    "Product Launch": [
        (r"\b(launch\w*|unveil\w*|announces? new|rolls? out|debut\w*|new (model|chip|service|product))\b", 3),
        (r"\b(release[sd]?|beta|pre-?orders?)\b", 1),
        (r"\bFDA approv\w*", 3),
    ],
    "Regulatory/Legal": [
        (r"\b(lawsuit|sues?|sued|fine[sd]?|probe|investigation|antitrust|settlement|sec charges|regulator\w*)\b", 2),
        (r"\b(subpoena|court|ruling|class action|penalt\w+|compliance failure)\b", 2),
    ],
    "Earnings": [
        (r"\b(earnings|eps|quarterly (results|profit)|revenue (rose|fell|beat|miss\w*)|guidance|profit warning)\b", 3),
        (r"\b(beat(s|ing)? estimates|misses? estimates|raises? outlook|cuts? outlook|dividend|buyback|record profit|growth accelerates)\b", 3),
    ],
    "Cyber/Operational": [
        (r"\b(cyber\w*|data breach|hack\w*|ransomware|outage|recall|supply chain disruption|strike|explosion|fire at)\b", 3),
        (r"\b(grounded|production halt|plant shutdown|systems? down)\b", 2),
    ],
}
BASE_SEVERITY = {
    "Geopolitical": 8, "Credit Event": 8, "Cyber/Operational": 7, "Macroeconomic": 6,
    "Regulatory/Legal": 6, "Merger/Acquisition": 5, "Earnings": 4, "Product Launch": 3, "Other": 2,
}

# ---- Finance sentiment lexicon (own compact, Loughran-McDonald-inspired list) ----
POS = {w: 1.0 for w in """gain gains surge surges surged soar soars soared rally rallies rallied jump jumps
beat beats strong stronger strength record growth profit profitable upgrade upgraded outperform bullish
rebound recover recovery boost boosts approve approved approval win wins breakthrough expand expands
improve improved improves optimistic robust resilient raises raised ceasefire accelerate demand
innovative success successful secure secures faster unveils launches debut cools crushing amazing impressive""".split()}
POS.update({"bull": 0.8, "buy": 0.5, "moon": 0.8, "pump": 0.4, "green": 0.4})
NEG = {w: 1.0 for w in """loss losses plunge plunges plunged slump slumps tumble tumbles tumbled crash crashes
miss misses missed weak weaker weakness decline declines declined fall falls fell drop drops dropped
downgrade downgraded bearish default defaults defaulted bankruptcy insolvency lawsuit probe fraud scandal
fine fined recall breach hack hacked outage layoffs cut cuts slash slashes warning warns fear fears
risk risks crisis recession sanctions war invasion strike halt halted collapse collapses bailout
shortfall volatile selloff sell-off downturn concern concerns trouble troubled disruption disrupted
tariff tariffs escalate escalates escalation""".split()}
NEG.update({"bear": 0.8, "dump": 0.6, "sell": 0.4, "rekt": 1.0, "red": 0.4, "tank": 0.9, "tanks": 0.9})
PHRASES = {  # multi-word cues override token scoring
    "beats estimates": 2.0, "tops estimates": 2.0, "raises outlook": 2.0, "record revenue": 2.0,
    "misses estimates": -2.0, "cuts outlook": -2.0, "profit warning": -2.5, "credit downgrade": -2.5,
    "files for bankruptcy": -3.0, "chapter 11": -3.0, "data breach": -2.0, "all-time high": 1.5,
    "price war": -1.0, "rate cut": 0.8, "rate hike": -0.8, "to the moon": 1.5, "going to zero": -2.0,
}
EMOJI = {"🚀": 1.2, "📈": 1.0, "💰": 0.5, "🔥": 0.3, "📉": -1.0, "💀": -1.2, "🩸": -1.0, "⚠️": -0.5}
NEGATORS = {"not", "no", "never", "without", "fails", "failed", "unlikely", "denies"}
INTENSIFIERS = {"plunge", "plunges", "plunged", "soar", "soars", "soared", "crash", "crashes", "crisis",
                "collapse", "collapses", "record", "massive", "huge", "breaking", "urgent", "historic",
                "emergency", "unprecedented", "panic", "surge", "surges", "tank", "tanks", "default"}

SOURCE_CREDIBILITY = {"news": 1.0, "rss": 0.9, "social": 0.5}
