"""Pluggable data sources. Every source yields dicts: id, ts (ISO UTC), source, text, engagement."""
import hashlib, json, os, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def _doc(source, text, ts, engagement=0, uid=None):
    uid = uid or hashlib.md5(f"{source}{text}".encode()).hexdigest()[:12]
    return {"id": uid, "ts": ts, "source": source, "text": text.strip(), "engagement": engagement}


class JsonlSource:
    """Replays a JSONL file (used for the reproducible demo and tests)."""
    def __init__(self, path): self.path = path
    def fetch(self):
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    yield _doc(d["source"], d["text"], d["ts"], d.get("engagement", 0), d.get("id"))


class RssSource:
    """Live news via any public RSS feed (stdlib only)."""
    def __init__(self, url="https://feeds.bbci.co.uk/news/business/rss.xml", limit=50):
        self.url, self.limit = url, limit
    def fetch(self):
        with urllib.request.urlopen(urllib.request.Request(self.url, headers={"User-Agent": "risk-engine"}), timeout=15) as r:
            root = ET.fromstring(r.read())
        for item in root.iter("item"):
            title = (item.findtext("title") or "") + ". " + (item.findtext("description") or "")
            try: ts = parsedate_to_datetime(item.findtext("pubDate")).astimezone(timezone.utc).isoformat()
            except Exception: ts = datetime.now(timezone.utc).isoformat()
            yield _doc("rss", title, ts)
            self.limit -= 1
            if self.limit <= 0: break


class NewsApiSource:
    """NewsAPI.org free tier. Needs env NEWSAPI_KEY."""
    def __init__(self, query="stocks OR earnings OR sanctions OR inflation", limit=50):
        self.query, self.limit = query, limit
    def fetch(self):
        key = os.environ["NEWSAPI_KEY"]
        url = "https://newsapi.org/v2/everything?" + urllib.parse.urlencode(
            {"q": self.query, "language": "en", "sortBy": "publishedAt", "pageSize": self.limit, "apiKey": key})
        with urllib.request.urlopen(url, timeout=15) as r:
            for a in json.load(r)["articles"]:
                yield _doc("news", f"{a['title']}. {a.get('description') or ''}", a["publishedAt"])


class RedditSource:
    """Social stream via Reddit's public JSON (r/stocks, r/wallstreetbets); engagement = upvotes."""
    def __init__(self, sub="stocks", limit=50): self.sub, self.limit = sub, limit
    def fetch(self):
        req = urllib.request.Request(f"https://www.reddit.com/r/{self.sub}/new.json?limit={self.limit}",
                                     headers={"User-Agent": "risk-engine"})
        with urllib.request.urlopen(req, timeout=15) as r:
            for p in json.load(r)["data"]["children"]:
                d = p["data"]
                ts = datetime.fromtimestamp(d["created_utc"], timezone.utc).isoformat()
                yield _doc("social", d["title"], ts, d.get("score", 0), d["id"])
