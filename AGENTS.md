# Codex task: Extend Microsoft Change Intelligence Agent with Marketing Security Digest

## Context

This repository contains a Microsoft Azure/M365 change intelligence collector. The current system collects and normalizes Microsoft change/security sources and exposes digest functionality, likely through a FastAPI endpoint and/or n8n integration.

The goal is to extend the existing system with a marketing-oriented digest layer for Microsoft security news.

This should not become a generic news scraper. It must collect Microsoft security-related updates, normalize them, classify their relevance, and generate marketing-friendly outputs that can be used by a marketing team for content planning, customer communication, LinkedIn posts, campaign triggers, and sales enablement.

## Objective

Implement a "Microsoft Security Marketing Digest" feature.

The feature must:

1. Collect or reuse Microsoft security/change events from existing sources.
2. Add a marketing relevance classification layer.
3. Generate digest output aimed at a non-technical marketing audience.
4. Clearly separate:
   - publishable external content candidates;
   - customer advisory opportunities;
   - internal awareness only;
   - items requiring security review before publication.
5. Prevent overclaiming by clearly marking preview, GA, tenant-specific, or technically uncertain information.

## Required sources

Use the existing collector architecture where possible. Extend rather than rebuild.

Prioritize official Microsoft sources already present or suitable for the existing pipeline:

- Microsoft Security Blog
- Microsoft Security Community Blog
- Microsoft 365 Message Center via Microsoft Graph Service Communications API
- Microsoft 365 Roadmap
- Intune What's New / In Development
- Defender What's New
- Entra What's New
- Security Copilot release notes
- Microsoft Partner Center announcements, if applicable

If a source already exists in the codebase, reuse it.
If a source does not exist yet, add it only when it fits the current architecture cleanly.

## Data model changes

Extend the normalized event model with marketing-specific fields.

Add fields similar to:

```json
{
  "marketing_relevant": true,
  "marketing_category": "publishable | customer_advisory | internal_awareness | review_required",
  "audience": ["CISO", "IT Manager", "Security Lead", "Compliance Officer", "SMB", "Enterprise"],
  "content_angle": ["Awareness", "Product update", "Risk advisory", "Thought leadership", "Campaign trigger", "Sales enablement"],
  "marketing_action": "Create LinkedIn post and customer advisory",
  "technical_depth": "executive | functional | technical",
  "urgency": "low | medium | high",
  "customer_impact": "Short explanation of why this matters to customers",
  "risk_of_overclaiming": "low | medium | high",
  "publication_guardrail": "Safe to publish | Security review required | Do not publish externally"
}
