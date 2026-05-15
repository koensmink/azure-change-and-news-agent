from datetime import datetime, timedelta, timezone
import json
from .db import query_events

def build_digest(hours: int = 24, security_only: bool = False, ga_only: bool = True, marketing_only: bool = False, include_review_required: bool = True, limit: int = 200, time_mode: str = "changed"):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    matched_rows = query_events(cutoff=cutoff, time_mode=time_mode, security_only=security_only, ga_only=ga_only, marketing_only=marketing_only, include_review_required=include_review_required, limit=1000000)
    returned_rows = matched_rows[:limit]
    items = [row_to_item(r, time_mode=time_mode) for r in returned_rows]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": hours,
        "time_mode": time_mode,
        "cutoff": cutoff.isoformat(),
        "security_only": security_only,
        "ga_only": ga_only,
        "marketing_only": marketing_only,
        "include_review_required": include_review_required,
        "limit": limit,
        "matched_count": len(matched_rows),
        "returned_count": len(items),
        "count": len(items),
        "items": items,
    }

def row_to_item(r: dict, time_mode: str = "changed") -> dict:
    if time_mode == "new":
        effective_at = r.get("first_seen_at")
        effective_at_source = "first_seen_at"
    elif time_mode == "seen":
        effective_at = r.get("last_seen_at")
        effective_at_source = "last_seen_at"
    elif time_mode == "new_or_changed":
        first_seen = r.get("first_seen_at")
        changed = r.get("last_changed_at")
        effective_at = first_seen if str(first_seen or "") >= str(changed or "") else changed
        effective_at_source = "first_seen_at" if str(first_seen or "") >= str(changed or "") else "last_changed_at"
    else:
        effective_at = r.get("last_changed_at")
        effective_at_source = "last_changed_at"
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
        "effective_at": effective_at,
        "effective_at_source": effective_at_source,
    }
