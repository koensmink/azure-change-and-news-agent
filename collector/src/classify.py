from .config import SECURITY_KEYWORDS

MICROSOFT_KEYWORDS = [
    "microsoft", "azure", "m365", "microsoft 365", "office 365", "entra", "defender", "intune", "purview",
    "sentinel", "security copilot", "exchange", "sharepoint", "onedrive", "teams", "windows", "graph",
]

PRODUCT_MAP = {
    "azure": "Azure",
    "microsoft 365": "Microsoft 365",
    "office 365": "Microsoft 365",
    "entra": "Entra ID",
    "defender": "Microsoft Defender",
    "intune": "Intune",
    "purview": "Purview",
    "sentinel": "Microsoft Sentinel",
    "security copilot": "Security Copilot",
    "exchange": "Exchange Online",
    "sharepoint": "SharePoint",
    "onedrive": "OneDrive",
    "teams": "Microsoft Teams",
    "windows": "Windows Security",
}


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


def classify_microsoft_relevance(event: dict) -> dict:
    hay = " ".join([
        event.get("title") or "",
        event.get("summary") or "",
        event.get("product") or "",
        event.get("body_text") or "",
        " ".join(event.get("tags") or []),
    ]).lower()

    source_owner = event.get("source_owner", "")
    if source_owner == "microsoft":
        event["microsoft_relevant"] = True
        event["microsoft_relevance_reason"] = "Microsoft-owned source"
    else:
        hit = next((k for k in MICROSOFT_KEYWORDS if k in hay), None)
        event["microsoft_relevant"] = bool(hit)
        event["microsoft_relevance_reason"] = (
            f"Third-party Microsoft-specific topic ({hit})" if hit else "No explicit Microsoft security angle"
        )

    products = []
    for k, p in PRODUCT_MAP.items():
        if k in hay and p not in products:
            products.append(p)
    event["affected_microsoft_products"] = products

    event["requires_review"] = source_owner != "microsoft"
    if source_owner != "microsoft":
        event["publication_guardrail"] = (
            "Security review required. Third-party source; validate against Microsoft or authoritative advisory before publication."
        )
    else:
        event["publication_guardrail"] = ""

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
