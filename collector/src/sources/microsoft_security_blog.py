import feedparser

FEED_URL = "https://www.microsoft.com/en-us/security/blog/feed/"


def fetch_index():
    feed = feedparser.parse(FEED_URL)
    return [{"id": e.get("id") or e.get("link"), "entry": e} for e in feed.entries]


def enrich_detail(item: dict) -> dict:
    e = item["entry"]
    tags = [t.get("term", "") for t in e.get("tags", []) if t.get("term")]
    return {
        "source": "microsoft_security_blog",
        "source_uid": item["id"],
        "source_url": e.get("link"),
        "title": e.get("title", ""),
        "summary": e.get("summary", ""),
        "product": "Microsoft Security",
        "tags": tags,
        "release_stage": "Unknown",
        "published_at": e.get("published", ""),
        "updated_at": e.get("updated", e.get("published", "")),
        "body_text": e.get("summary", ""),
        "raw": {"entry": dict(e)},
    }
