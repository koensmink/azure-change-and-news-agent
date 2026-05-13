from datetime import datetime, timedelta, timezone
import json
from .db import query_events

def build_digest(hours: int = 24, security_only: bool = True, ga_only: bool = True, limit: int = 200):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    rows = query_events(since_iso=since, security_only=security_only, ga_only=ga_only, limit=limit)

    # Only include NEW/CHANGED by default signal (still stored in DB even if unchanged)
    items = []
    for r in rows:
        if r.get("change_type") in ("NEW", "CHANGED"):
            items.append(row_to_item(r))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": hours,
        "security_only": security_only,
        "ga_only": ga_only,
        "count": len(items),
        "items": items,
    }

def row_to_item(r: dict) -> dict:
    return {
        "event_id": r["event_id"],
        "change_type": r.get("change_type"),
        "source": r["source"],
        "source_url": r["source_url"],
        "title": r["title"],
        "summary": r.get("summary"),
        "product": r.get("product"),
        "release_stage": r.get("release_stage"),
        "published_at": r.get("published_at"),
        "updated_at": r.get("updated_at"),
        "security_relevant": bool(r.get("security_relevant")),
        "security_reason": r.get("security_reason"),
        "category": r.get("category"),
        "impact": r.get("impact"),
        "recommended_action": r.get("recommended_action"),
        "microsoft_relevant": bool(r.get("microsoft_relevant")),
        "microsoft_relevance_reason": r.get("microsoft_relevance_reason"),
        "affected_microsoft_products": json.loads(r.get("affected_microsoft_products") or "[]") if isinstance(r.get("affected_microsoft_products"), str) else (r.get("affected_microsoft_products") or []),
        "source_confidence": r.get("source_confidence"),
        "publication_guardrail": r.get("publication_guardrail"),
    }
