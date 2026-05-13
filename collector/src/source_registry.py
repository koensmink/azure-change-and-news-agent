from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .sources import (
    azure_updates,
    defender_whatsnew,
    entra_whatsnew,
    graph_message_center,
    intune_whatsnew,
    m365_roadmap,
    microsoft_security_blog,
    third_party_rss,
)


@dataclass(frozen=True)
class SourceDefinition:
    name: str
    source_type: str
    owner: str
    confidence: str
    default_enabled: bool
    max_items: int
    fetch_index: Callable[[], list[dict]]
    enrich_detail: Callable[[dict], dict]


SOURCE_DEFINITIONS: dict[str, SourceDefinition] = {
    "graph_message_center": SourceDefinition(
        name="graph_message_center",
        source_type="api",
        owner="microsoft",
        confidence="official_microsoft",
        default_enabled=True,
        max_items=200,
        fetch_index=graph_message_center.fetch_index,
        enrich_detail=graph_message_center.enrich_detail,
    ),
    "m365_roadmap": SourceDefinition("m365_roadmap", "official_feed", "microsoft", "official_microsoft", True, 200, m365_roadmap.fetch_index, lambda i: m365_roadmap.enrich_detail(i, mode="json")),
    "intune_whatsnew": SourceDefinition("intune_whatsnew", "official_docs", "microsoft", "official_microsoft", True, 80, intune_whatsnew.fetch_index, intune_whatsnew.enrich_detail),
    "defender_whatsnew": SourceDefinition("defender_whatsnew", "official_docs", "microsoft", "official_microsoft", True, 80, defender_whatsnew.fetch_index, defender_whatsnew.enrich_detail),
    "entra_whatsnew": SourceDefinition("entra_whatsnew", "official_docs", "microsoft", "official_microsoft", True, 120, entra_whatsnew.fetch_index, entra_whatsnew.enrich_detail),
    "azure_updates": SourceDefinition("azure_updates", "official_feed", "microsoft", "official_microsoft", True, 200, azure_updates.fetch_index, azure_updates.enrich_detail),
    "microsoft_security_blog": SourceDefinition("microsoft_security_blog", "official_blog", "microsoft", "official_microsoft", True, 100, microsoft_security_blog.fetch_index, microsoft_security_blog.enrich_detail),
    "third_party_rss": SourceDefinition("third_party_rss", "third_party_feed", "external", "trusted_security_vendor", True, 100, third_party_rss.fetch_index, third_party_rss.enrich_detail),
}
