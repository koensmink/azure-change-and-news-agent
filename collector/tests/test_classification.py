import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.classify import classify_microsoft_relevance


def test_official_microsoft_source_included():
    e = classify_microsoft_relevance({"title": "Update", "source_owner": "microsoft"})
    assert e["microsoft_relevant"] is True
    assert "Microsoft-owned" in e["microsoft_relevance_reason"]


def test_third_party_microsoft_specific_included():
    e = classify_microsoft_relevance({"title": "Phishing hits Microsoft 365 tenants", "source_owner": "external"})
    assert e["microsoft_relevant"] is True


def test_generic_non_microsoft_excluded():
    e = classify_microsoft_relevance({"title": "Linux kernel CVE roundup", "source_owner": "external"})
    assert e["microsoft_relevant"] is False


def test_third_party_requires_review():
    e = classify_microsoft_relevance({"title": "Azure OAuth abuse", "source_owner": "external"})
    assert e["requires_review"] is True
    assert "Security review required" in e["publication_guardrail"]


def test_source_confidence_assignment_example():
    event = {"title": "Defender update", "source_owner": "microsoft", "source_confidence": "official_microsoft"}
    assert event["source_confidence"] == "official_microsoft"
