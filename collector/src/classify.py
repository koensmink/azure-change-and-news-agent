from .config import SECURITY_KEYWORDS

def classify_security(event: dict) -> dict:
    hay = " ".join([
        event.get("title") or "",
        event.get("summary") or "",
        event.get("product") or "",
        event.get("body_text") or "",
        " ".join(event.get("tags") or []),
    ]).lower()

    hits = [k for k in SECURITY_KEYWORDS if k.lower() in hay]

    if hits:
        event["security_relevant"] = True
        event["security_reason"] = f"keyword_hit={','.join(hits[:12])}"
        event["category"] = _guess_category(hay)
        event["impact"] = "Unknown"
        event["recommended_action"] = "Review change; assess impact on policies, identity, endpoints, logging."
    else:
        event["security_relevant"] = False
        event["security_reason"] = None
        event["category"] = "Other"
        event["impact"] = "Unknown"
        event["recommended_action"] = None

    return event


def classify_marketing(event: dict) -> dict:
    hay = " ".join([
        event.get("title") or "",
        event.get("summary") or "",
        event.get("product") or "",
        event.get("body_text") or "",
        " ".join(event.get("tags") or []),
    ]).lower()

    security_relevant = bool(event.get("security_relevant"))
    marketing_relevant = security_relevant

    category = _marketing_category(hay, security_relevant)
    audience = _audience(hay)
    content_angle = _content_angle(hay, category)
    technical_depth = _technical_depth(hay)
    urgency = _urgency(hay)
    risk_of_overclaiming = _overclaim_risk(event, hay)
    publication_guardrail = _publication_guardrail(category, risk_of_overclaiming)

    event["marketing_relevant"] = marketing_relevant
    event["marketing_category"] = category
    event["audience"] = audience
    event["content_angle"] = content_angle
    event["marketing_action"] = _marketing_action(category, urgency, risk_of_overclaiming)
    event["technical_depth"] = technical_depth
    event["urgency"] = urgency
    event["customer_impact"] = _customer_impact(event, category, urgency)
    event["risk_of_overclaiming"] = risk_of_overclaiming
    event["publication_guardrail"] = publication_guardrail
    return event

def _guess_category(hay: str) -> str:
    if any(w in hay for w in ["entra", "conditional access", "mfa", "fido", "passkey", "identity", "pim", "rbac"]):
        return "Identity"
    if any(w in hay for w in ["intune", "endpoint", "device", "compliance", "autopilot"]):
        return "Endpoint"
    if any(w in hay for w in ["defender", "xdr", "sentinel", "siem", "soar"]):
        return "Security"
    if any(w in hay for w in ["firewall", "private endpoint", "vnet", "network", "dns", "ddos"]):
        return "Networking"
    if any(w in hay for w in ["policy", "audit", "logging", "compliance", "governance"]):
        return "Compliance"
    return "Other"


def _marketing_category(hay: str, security_relevant: bool) -> str:
    if not security_relevant:
        return "internal_awareness"
    if any(k in hay for k in ["preview", "private preview", "public preview", "roadmap", "in development"]):
        return "review_required"
    if any(k in hay for k in ["incident", "vulnerability", "cve", "breach", "critical", "exploit"]):
        return "customer_advisory"
    return "publishable"


def _audience(hay: str) -> list[str]:
    base = ["Security Lead", "IT Manager"]
    if any(k in hay for k in ["compliance", "audit", "governance", "regulatory"]):
        base.append("Compliance Officer")
    if any(k in hay for k in ["identity", "entra", "mfa", "conditional access"]):
        base.append("CISO")
    if any(k in hay for k in ["enterprise", "tenant"]):
        base.append("Enterprise")
    else:
        base.append("SMB")
    return list(dict.fromkeys(base))


def _content_angle(hay: str, category: str) -> list[str]:
    out = ["Awareness"]
    if any(k in hay for k in ["release", "general availability", "ga", "now available", "what's new"]):
        out.append("Product update")
    if category == "customer_advisory":
        out.append("Risk advisory")
    if any(k in hay for k in ["roadmap", "preview", "in development"]):
        out.append("Thought leadership")
    out.append("Sales enablement")
    return list(dict.fromkeys(out))


def _technical_depth(hay: str) -> str:
    if any(k in hay for k in ["api", "schema", "powershell", "json", "graph"]):
        return "technical"
    if any(k in hay for k in ["policy", "configuration", "admin center"]):
        return "functional"
    return "executive"


def _urgency(hay: str) -> str:
    if any(k in hay for k in ["critical", "urgent", "immediately", "incident", "active exploitation"]):
        return "high"
    if any(k in hay for k in ["retire", "deprecate", "deadline", "enforcement"]):
        return "medium"
    return "low"


def _overclaim_risk(event: dict, hay: str) -> str:
    stage = (event.get("release_stage") or "Unknown").lower()
    if stage != "ga":
        return "high"
    if any(k in hay for k in ["tenant", "may vary", "rollout", "limited"]):
        return "medium"
    return "low"


def _publication_guardrail(category: str, overclaim_risk: str) -> str:
    if category == "review_required" or overclaim_risk == "high":
        return "Security review required"
    if category == "internal_awareness":
        return "Do not publish externally"
    return "Safe to publish"


def _marketing_action(category: str, urgency: str, overclaim_risk: str) -> str:
    if category == "customer_advisory":
        return "Create customer advisory and coordinate account outreach."
    if category == "review_required" or overclaim_risk == "high":
        return "Draft internal brief; obtain security review before publishing."
    if urgency == "high":
        return "Publish fast update and notify sales team."
    return "Create LinkedIn post and monthly digest summary."


def _customer_impact(event: dict, category: str, urgency: str) -> str:
    product = event.get("product") or "Microsoft security stack"
    if category == "customer_advisory":
        return f"Customers may need immediate checks in {product} to reduce exposure."
    if urgency == "medium":
        return f"Customers should plan configuration updates in {product} before enforcement timelines."
    return f"This update can influence customer security posture and roadmap decisions for {product}."
