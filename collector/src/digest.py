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
    audience = r.get("audience")
    content_angle = r.get("content_angle")
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
        "marketing_relevant": bool(r.get("marketing_relevant")),
        "marketing_category": r.get("marketing_category"),
        "audience": json.loads(audience) if isinstance(audience, str) and audience else (audience or []),
        "content_angle": json.loads(content_angle) if isinstance(content_angle, str) and content_angle else (content_angle or []),
        "marketing_action": r.get("marketing_action"),
        "technical_depth": r.get("technical_depth"),
        "urgency": r.get("urgency"),
        "customer_impact": r.get("customer_impact"),
        "risk_of_overclaiming": r.get("risk_of_overclaiming"),
        "publication_guardrail": r.get("publication_guardrail"),
        "source_reference": {
            "url": r["source_url"],
            "source": r["source"],
            "official_public_source": True,
            "public_downloadable": True,
        },
    }


def build_marketing_digest(hours: int = 24, ga_only: bool = False, limit: int = 300):
    payload = build_digest(hours=hours, security_only=True, ga_only=ga_only, limit=limit)
    items = [it for it in payload["items"] if it.get("marketing_relevant")]
    grouped = {
        "publishable": [],
        "customer_advisory": [],
        "internal_awareness": [],
        "review_required": [],
    }
    for it in items:
        grouped.setdefault(it.get("marketing_category") or "internal_awareness", []).append(it)

    payload["digest_type"] = "microsoft_security_marketing_digest"
    payload["count"] = len(items)
    payload["items"] = items
    payload["grouped"] = grouped
    return payload
