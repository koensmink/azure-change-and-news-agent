import os
import feedparser

RSS_URLS = [u.strip() for u in os.getenv("THIRD_PARTY_RSS_URLS", "").split(",") if u.strip()]


def fetch_index():
    items = []
    for url in RSS_URLS:
        feed = feedparser.parse(url)
        for e in feed.entries:
            items.append({"feed": url, "id": e.get("id") or e.get("link"), "entry": e})
    return items


def enrich_detail(item: dict) -> dict:
    e = item["entry"]
    tags = [t.get("term", "") for t in e.get("tags", []) if t.get("term")]
    return {
        "source": "third_party_rss",
        "source_uid": item["id"],
        "source_url": e.get("link"),
        "title": e.get("title", ""),
        "summary": e.get("summary", ""),
        "product": "Third-party Microsoft security",
        "tags": tags,
        "release_stage": "Unknown",
        "published_at": e.get("published", ""),
        "updated_at": e.get("updated", e.get("published", "")),
        "body_text": e.get("summary", ""),
        "raw": {"entry": dict(e), "feed": item.get("feed")},
    }
