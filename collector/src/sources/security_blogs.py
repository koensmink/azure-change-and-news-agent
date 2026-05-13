import requests
from bs4 import BeautifulSoup

FEEDS = {
    "microsoft_security_blog": "https://www.microsoft.com/en-us/security/blog/feed/",
    "microsoft_security_community_blog": "https://techcommunity.microsoft.com/category/microsoft-security/blog/microsoft-security-blog/rss",
    "security_copilot_release_notes": "https://techcommunity.microsoft.com/category/microsoft-security/blog/microsoft-security-copilot-blog/rss",
}


def fetch_index(source_name: str):
    feed_url = FEEDS[source_name]
    r = requests.get(feed_url, timeout=30, headers={"User-Agent": "ms-changes-collector/1.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")
    items = []
    for item in soup.select("channel > item")[:80]:
        title = (item.title.get_text() if item.title else "").strip()
        link = (item.link.get_text() if item.link else "").strip()
        guid = (item.guid.get_text() if item.guid else link).strip()
        pub = (item.pubDate.get_text() if item.pubDate else None)
        if not title or not link:
            continue
        items.append(
            {
                "source": source_name,
                "title": title,
                "url": link,
                "guid": guid,
                "published_at": pub,
                "feed_url": feed_url,
            }
        )
    return items


def enrich_detail(idx: dict) -> dict:
    url = idx["url"]
    r = requests.get(url, timeout=30, headers={"User-Agent": "ms-changes-collector/1.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)
    summary = None
    m = soup.find("meta", attrs={"name": "description"})
    if m and m.get("content"):
        summary = m["content"].strip()

    stage = "GA"
    hay = f"{idx['title']} {summary or ''} {text}".lower()
    if "preview" in hay:
        stage = "Preview"

    return {
        "source": idx["source"],
        "source_uid": idx["guid"],
        "source_url": url,
        "title": idx["title"][:300],
        "summary": summary,
        "product": "Microsoft Security",
        "tags": ["security", "official_blog"],
        "release_stage": stage,
        "published_at": idx.get("published_at"),
        "updated_at": None,
        "body_text": text[:20000],
        "raw": {"feed_url": idx.get("feed_url"), "article_url": url},
    }
