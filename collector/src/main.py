import time
import threading
from datetime import datetime, timezone
from croniter import croniter

from .api import app
from .config import RUN_SCHEDULE_CRON, PORT, INCLUDE_SOURCES
from .db import init_db, upsert_event
from .normalize import make_event_id, make_content_hash, stable_url
from .classify import classify_security, classify_microsoft_relevance
from .source_registry import SOURCE_DEFINITIONS

# sources
from .sources import graph_message_center, m365_roadmap, intune_whatsnew, defender_whatsnew, entra_whatsnew, azure_updates

import uvicorn

def ingest_source(source_name: str) -> int:
    definition = SOURCE_DEFINITIONS.get(source_name)
    if not definition:
        return 0

    count = 0
    index_payload = definition.fetch_index()
    if isinstance(index_payload, dict) and source_name == "m365_roadmap":
        mode = index_payload.get("mode", "json")
        items = index_payload.get("items", [])
        for item in items[: definition.max_items]:
            detail = m365_roadmap.enrich_detail(item, mode=mode)
            detail["source_confidence"] = definition.confidence
            detail["source_owner"] = definition.owner
            count += ingest_detail(detail)
        return count

    for item in index_payload[: definition.max_items]:
        detail = definition.enrich_detail(item)
        detail["source_confidence"] = definition.confidence
        detail["source_owner"] = definition.owner
        count += ingest_detail(detail)
    return count

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
    detail = classify_microsoft_relevance(detail)

    if not detail.get("microsoft_relevant"):
        return 0

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
