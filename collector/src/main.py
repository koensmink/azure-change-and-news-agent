import time
import threading
from datetime import datetime, timezone
from croniter import croniter

from .api import app
from .config import RUN_SCHEDULE_CRON, PORT, INCLUDE_SOURCES, DEFAULT_GA_ONLY
from .db import init_db, upsert_event
from .normalize import make_event_id, make_content_hash, stable_url
from .classify import classify_security, classify_marketing

# sources
from .sources import graph_message_center, m365_roadmap, intune_whatsnew, defender_whatsnew, entra_whatsnew, azure_updates, security_blogs

import uvicorn

def ingest_source(source_name: str) -> int:
    count = 0

    if source_name == "graph_message_center":
        index = graph_message_center.fetch_index()
        for msg in index:
            detail = graph_message_center.enrich_detail(msg)
            count += ingest_detail(detail)
        return count

    if source_name == "m365_roadmap":
        res = m365_roadmap.fetch_index()
        mode = res["mode"]
        for item in res["items"]:
            detail = m365_roadmap.enrich_detail(item, mode=mode)
            count += ingest_detail(detail)
        return count

    if source_name == "intune_whatsnew":
        index = intune_whatsnew.fetch_index()
        for it in index[:80]:
            detail = intune_whatsnew.enrich_detail(it)
            count += ingest_detail(detail)
        return count

    if source_name == "defender_whatsnew":
        index = defender_whatsnew.fetch_index()
        for it in index[:80]:
            detail = defender_whatsnew.enrich_detail(it)
            count += ingest_detail(detail)
        return count

    if source_name == "entra_whatsnew":
        index = entra_whatsnew.fetch_index()
        for it in index[:120]:
            detail = entra_whatsnew.enrich_detail(it)
            count += ingest_detail(detail)
        return count

    if source_name == "azure_updates":
        index = azure_updates.fetch_index()
        for it in index[:200]:
            detail = azure_updates.enrich_detail(it)
            count += ingest_detail(detail)
        return count

    if source_name in ("microsoft_security_blog", "microsoft_security_community_blog", "security_copilot_release_notes"):
        index = security_blogs.fetch_index(source_name)
        for it in index:
            detail = security_blogs.enrich_detail(it)
            count += ingest_detail(detail)
        return count

    return 0

def ingest_detail(detail: dict) -> int:
    # Normalize + hashes
    detail["source_url"] = stable_url(detail["source_url"])
    event_id = make_event_id(detail["source"], detail.get("source_uid", ""), detail["source_url"])
    detail["event_id"] = event_id

    content_hash = make_content_hash({
        "title": detail.get("title"),
        "summary": detail.get("summary"),
        "product": detail.get("product"),
        "release_stage": detail.get("release_stage"),
        "published_at": detail.get("published_at"),
        "updated_at": detail.get("updated_at"),
        "tags": detail.get("tags"),
        "body_text": detail.get("body_text"),
    })
    detail["content_hash"] = content_hash

    # Security classification
    detail = classify_security(detail)
    detail = classify_marketing(detail)

    # Persist (DB determines NEW/CHANGED/UNCHANGED)
    change_type = upsert_event(detail)

    # GA-only? (we still store everything; filtering happens in API/digest)
    return 1

def run_pipeline():
    total = 0
    for s in INCLUDE_SOURCES:
        try:
            n = ingest_source(s)
            total += n
            print(f"[{datetime.now(timezone.utc).isoformat()}] source={s} ingested={n}")
        except Exception as ex:
            print(f"[{datetime.now(timezone.utc).isoformat()}] source={s} error={ex}")
    print(f"[{datetime.now(timezone.utc).isoformat()}] pipeline done total={total}")

def scheduler_loop():
    base = datetime.now(timezone.utc)
    itr = croniter(RUN_SCHEDULE_CRON, base)
    while True:
        next_run = itr.get_next(datetime)
        now = datetime.now(timezone.utc)
        sleep_s = max(0, (next_run - now).total_seconds())
        time.sleep(sleep_s)
        run_pipeline()

def main():
    init_db()
    # Run once on startup (useful for first fill)
    run_pipeline()

    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
