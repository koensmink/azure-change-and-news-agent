# AGENTS.md addition: Microsoft Security Marketing Digest source scope

## Source scope

The marketing digest must not be limited to the sources currently implemented in the repository.

The system should be able to collect, normalize, and classify Microsoft-relevant security news from a broader set of sources, as long as the content is clearly applicable to Microsoft security, Microsoft cloud, Microsoft 365, Azure, Entra ID, Defender, Intune, Purview, Sentinel, Security Copilot, Windows security, or the Microsoft partner/security ecosystem.

The goal is to support the marketing department with relevant Microsoft security news, not to build a generic cybersecurity news aggregator.

## Source selection principles

Sources may include, but are not limited to:

- Official Microsoft blogs and documentation
- Microsoft Security Blog
- Microsoft Tech Community
- Microsoft Learn release notes
- Microsoft 365 Message Center
- Microsoft 365 Roadmap
- Microsoft Graph Service Communications API
- Microsoft Partner Center announcements
- Microsoft Security Response Center
- Microsoft CVE/security update guidance
- Microsoft Defender / Entra / Intune / Purview / Sentinel product updates
- Security Copilot updates
- Azure Updates
- Relevant third-party security news when the topic directly affects Microsoft products or services

Third-party sources are allowed only when the article is clearly Microsoft-specific or materially relevant to Microsoft security customers.

Examples of allowed third-party topics:

- A vulnerability affecting Microsoft Exchange, SharePoint, Windows, Azure, Entra ID, or Microsoft 365
- Threat actor activity targeting Microsoft 365 tenants
- Phishing campaigns abusing Microsoft services
- Security research about Microsoft identity, OAuth, Teams, OneDrive, SharePoint, or Azure
- Public incidents or advisories involving Microsoft cloud or Microsoft security products
- Regulatory or compliance changes that directly affect Microsoft security positioning

Examples of sources that should normally be excluded:

- Generic cybersecurity news without a Microsoft angle
- Vendor marketing content that only compares against Microsoft without factual security relevance
- Opinion pieces without verifiable technical claims
- Unverified social media posts
- Rumors without authoritative confirmation
- General AI/security hype without a Microsoft product or customer impact angle

## Source confidence and trust model

Every collected item must include a source confidence classification.

Use the following levels:

```json
{
  "source_confidence": "official_microsoft | official_government | trusted_security_vendor | reputable_news | community | unverified"
}
```

Apply the following rules:

- `official_microsoft` is preferred for publication.
- `official_government` may be used for vulnerability, threat, or regulatory context.
- `trusted_security_vendor` may be used when the content is technically specific and Microsoft-relevant.
- `reputable_news` may be used for public incident or market context.
- `community` content must normally be marked as `review_required`.
- `unverified` content must not be marked as publishable.

## Microsoft relevance classification

Add or extend classification logic with a dedicated Microsoft relevance field.

Example event fields:

```json
{
  "microsoft_relevant": true,
  "microsoft_relevance_reason": "The item describes a phishing campaign targeting Microsoft 365 tenants.",
  "affected_microsoft_products": [
    "Microsoft 365",
    "Exchange Online",
    "Microsoft Defender for Office 365"
  ]
}
```

An item should only be included in the marketing digest when:

```text
microsoft_relevant = true
```

or when it has a clear manually configured allowlist reason.

## Required filtering behavior

The system must distinguish between:

1. Microsoft-owned source
2. Microsoft-specific topic from a third-party source
3. Generic security topic with weak Microsoft relevance

Only categories 1 and 2 should be included by default.

Category 3 should be excluded unless explicitly requested.

## Marketing digest goal

The digest is intended for the marketing department and should focus on Microsoft-related security topics that can support:

- LinkedIn content
- blog planning
- customer advisories
- campaign triggers
- sales enablement
- Microsoft security proposition messaging
- security awareness content
- partner positioning

The output should translate technical Microsoft security updates into clear marketing relevance.

It should not produce generic SOC, threat intelligence, or vulnerability reporting unless the Microsoft relevance is explicit.

## Publication guardrails for non-Microsoft sources

For third-party sources, apply stricter publication guardrails.

Rules:

- Do not mark third-party content as `publishable` unless the Microsoft relevance is explicit and the technical claim is verifiable.
- Prefer `review_required` for third-party research, vendor blogs, and community posts.
- If the item discusses a vulnerability, exploit, incident, or breach, require security review before external publication.
- If Microsoft has not confirmed the claim, include that limitation in the output.
- If source confidence is `community` or `unverified`, do not recommend external publication.

Example guardrail:

```json
{
  "publication_guardrail": "Security review required. Third-party source; validate against Microsoft or authoritative advisory before publication."
}
```

## Additional source discovery

When implementing new collectors, design the source layer so additional Microsoft-relevant sources can be added without large refactoring.

Preferred approach:

- Config-driven source definitions where possible
- Clear source type metadata
- Per-source parser/normalizer
- Common normalized event schema
- Shared relevance and marketing classification layer

The system should support adding future sources such as RSS feeds, official APIs, Microsoft Learn pages, vendor advisories, or curated allowlisted URLs.

## Acceptance criteria addition

The implementation must be considered incomplete unless:

1. The digest can include Microsoft-relevant items from sources beyond the currently implemented source list.
2. Each item includes `microsoft_relevant`, `microsoft_relevance_reason`, and `affected_microsoft_products` where applicable.
3. Each item includes `source_confidence`.
4. Third-party items are handled with stricter publication guardrails.
5. Generic cybersecurity news without a Microsoft-specific angle is excluded by default.
6. The README documents how new Microsoft-relevant sources can be added.
7. Tests cover:
   - official Microsoft source inclusion;
   - third-party Microsoft-specific inclusion;
   - generic non-Microsoft security news exclusion;
   - third-party source requiring review;
   - source confidence assignment.

## Compact addition to the original Codex task

Place this under the Objective section:

```markdown
The system must support sources beyond the currently implemented ones. The scope is Microsoft-relevant security news for marketing purposes, not only Microsoft-owned sources and not generic cybersecurity news. Third-party sources are allowed when the item clearly affects Microsoft products, Microsoft cloud services, Microsoft security customers, or Microsoft security positioning.
```

Place this under Implementation constraints:

```markdown
Do not hardcode the source list as final. Implement the source layer so additional Microsoft-relevant sources can be added later with minimal changes. Use source metadata and relevance classification to decide whether an item belongs in the marketing digest.
```

## Design recommendation

Make Microsoft relevance a separate classifier next to `security_relevant` and `marketing_relevant`. This prevents generic security news from entering the marketing digest without a clear Microsoft angle.
