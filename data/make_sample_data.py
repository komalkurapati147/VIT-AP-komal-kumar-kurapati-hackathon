"""Generates the synthetic (original, hand-written) demo corpus + synthetic wholesale portfolio.
All text is invented for demonstration; no copyrighted articles are bundled."""
import json, random, csv
from datetime import datetime, timedelta, timezone

T0 = datetime(2026, 10, 6, 13, 30, tzinfo=timezone.utc)  # replay start
NEWS = [  # (minute offset, text)
 (0, "Apple unveils new iPhone model with faster chip, pre-orders open Friday"),
 (10, "Nvidia beats estimates as data-centre demand drives record revenue"),
 (25, "Fed signals rate cut as inflation cools; Treasury yields fall"),
 (40, "Boeing faces probe after fresh safety investigation; shares tumble"),
 (55, "Tesla recall hits thousands of vehicles over software fault"),
 (70, "Exxon Mobil to acquire shale producer in all-cash deal valued at $6 billion"),
 (85, "Sanctions escalate as military tensions rise; oil supply fears grip markets"),
 (100, "Intel misses estimates and cuts outlook as chip demand weakens"),
 (115, "JPMorgan posts strong quarterly profit, raises outlook on lending growth"),
 (130, "Bank of America downgraded as credit losses and loan defaults mount"),
 (145, "Pfizer wins FDA approval for new vaccine, shares rally"),
 (160, "Netflix launches ad-supported bundle; analysts optimistic on subscriber growth"),
 (175, "Walmart steady as consumer spending holds up, no change to guidance"),
 (190, "Disney hit by lawsuit from shareholders over streaming disclosures"),
 (205, "Amazon AWS outage disrupts thousands of customers for several hours"),
 (220, "Goldman Sachs warns of recession risk and sharp slowdown in deal activity"),
 (235, "Chevron rebounds as crude rallies on supply disruption"),
 (250, "Microsoft Azure growth accelerates, beating estimates; record profit"),
 (265, "Coca-Cola reports steady earnings, dividend unchanged"),
 (280, "Meta fined by regulators in antitrust settlement over data practices"),
 (295, "Johnson & Johnson faces class action ruling; investors fear further penalties"),
 (310, "Trade war deepens: new tariffs and export controls shake supply chains"),
 (325, "Boeing files for chapter 11 protection of key supplier; credit downgrade looms"),
 (340, "Alphabet announces new AI service debut with strong early demand"),
]
SOCIAL = [  # (offset, text, engagement)
 (5, "$NVDA earnings were insane 🚀🚀 bullish all the way", 5400),
 (12, "AAPL new iPhone looks meh, not impressed. selling", 120),
 (30, "Rate cut incoming?? markets rally 📈", 900),
 (42, "BA is a disaster, another investigation. going to zero 📉", 2300),
 (57, "RT @trader: Tesla recall again 💀 TSLA tank", 300),
 (60, "RT @trader: Tesla recall again 💀 TSLA tank", 280),
 (88, "WAR escalating, sanctions everywhere, oil spiking. BREAKING", 15000),
 (102, "Intel guidance is awful, $INTC dump incoming 🩸", 700),
 (118, "JPM crushing it, strong quarter 💰", 450),
 (132, "BofA credit downgrade?? this is bad ⚠️", 1800),
 (148, "Pfizer approval!! PFE to the moon 🚀", 3100),
 (162, "Netflix ads tier is a win, NFLX bullish", 650),
 (178, "Walmart boring but fine", 40),
 (192, "Disney lawsuit, DIS red again", 210),
 (207, "AWS is down AGAIN. Amazon outage is a huge problem!", 8800),
 (222, "Goldman says recession risk is rising, fear everywhere 📉", 2600),
 (252, "Azure beat. MSFT record growth 📈", 1400),
 (268, "KO dividend unchanged, nothing to see", 25),
 (282, "Meta fined again, regulators finally acting", 900),
 (300, "J&J penalties could be massive, JNJ risk rising ⚠️", 760),
 (312, "Tariffs + export controls = supply chain crisis. TRADE WAR is here!", 12000),
 (327, "BA supplier chapter 11, credit downgrade next?? default fears", 4200),
 (342, "Google AI launch looks amazing, GOOGL strong 🚀", 2100),
 (350, "Crypto bros have no idea what's coming", 15),
]

def write():
    def ts(m): return (T0 + timedelta(minutes=m)).isoformat()
    with open("data/sample_news.jsonl", "w", encoding="utf-8") as f:
        for m, t in NEWS: f.write(json.dumps({"source": "news", "ts": ts(m), "text": t}) + "\n")
    with open("data/sample_social.jsonl", "w", encoding="utf-8") as f:
        for m, t, e in SOCIAL: f.write(json.dumps({"source": "social", "ts": ts(m), "text": t, "engagement": e}) + "\n")

    random.seed(42)
    rows, i = [], 1
    cps = [("Meridian Steel", "Materials", "US", "BBB"), ("Northwind Energy", "Energy", "US", "BB"),
           ("Helios Airlines", "Industrials", "EU", "BB"), ("Atlas Retail", "Consumer", "US", "BBB"),
           ("Pacifica Shipping", "Industrials", "APAC", "B"), ("Orion Telecom", "Communication", "EU", "A"),
           ("Vertex Pharma", "Healthcare", "US", "A"), ("Sable Mining", "Materials", "EM", "B"),
           ("Quantum Tech", "Technology", "US", "A"), ("Cobalt Bank", "Financials", "EU", "BBB")]
    def add(**k):
        nonlocal i; rows.append({"position_id": f"P{i:03d}", **k}); i += 1
    base = dict(counterparty="", sector="", country="", rating="", notional=0, market_value=0, duration=0.0,
                spread_duration=0.0, dv01=0.0, pd=0.0, lgd=0.45, direction=1, beta=0.0, currency="USD")
    for cp, sec, ctry, rt in cps:
        n = random.choice([20, 35, 50, 80]) * 1e6
        pd = {"A": .004, "BBB": .01, "BB": .03, "B": .07}[rt]
        add(**{**base, "asset_class": "Loan", "counterparty": cp, "sector": sec, "country": ctry, "rating": rt,
               "notional": n, "market_value": n * .99, "spread_duration": 3.2, "pd": pd})
        b = random.choice([10, 15, 25]) * 1e6
        add(**{**base, "asset_class": "Bond", "counterparty": cp, "sector": sec, "country": ctry, "rating": rt,
               "notional": b, "market_value": b * random.uniform(.96, 1.02), "duration": random.uniform(3, 8),
               "spread_duration": random.uniform(3, 7)})
    for tkr, sec, beta in [("AAPL", "Technology", 1.2), ("JPM", "Financials", 1.1), ("XOM", "Energy", .9),
                           ("BA", "Industrials", 1.4), ("PFE", "Healthcare", .7), ("WMT", "Consumer", .6)]:
        v = random.choice([8, 12, 20]) * 1e6
        add(**{**base, "asset_class": "Equity", "counterparty": tkr, "sector": sec, "country": "US",
               "rating": "A", "notional": v, "market_value": v, "beta": beta})
    for k in range(4):
        add(**{**base, "asset_class": "IRS", "counterparty": "Cobalt Bank", "sector": "Financials", "country": "EU",
               "rating": "BBB", "notional": 100e6, "market_value": random.uniform(-.5e6, .8e6),
               "dv01": 45000 * (k + 1) / 2, "direction": 1 if k % 2 == 0 else -1})  # +1 receive-fixed, -1 pay-fixed
    for ccy, d in [("EUR", 1), ("JPY", -1), ("INR", 1), ("BRL", 1)]:
        add(**{**base, "asset_class": "FX_Forward", "counterparty": "Orion Telecom", "sector": "Communication",
               "country": "EU", "rating": "A", "notional": 40e6, "market_value": 0.2e6, "direction": d, "currency": ccy})
    for d in (1, -1):
        add(**{**base, "asset_class": "Commodity_Swap", "counterparty": "Northwind Energy", "sector": "Energy",
               "country": "US", "rating": "BB", "notional": 30e6, "market_value": 0.1e6, "direction": d})
    with open("data/sample_portfolio.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"news={len(NEWS)} social={len(SOCIAL)} positions={len(rows)}")

if __name__ == "__main__":
    write()
