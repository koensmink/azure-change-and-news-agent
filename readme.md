## Objective

The system must support sources beyond the currently implemented ones. The scope is Microsoft-relevant security news for marketing purposes, not only Microsoft-owned sources and not generic cybersecurity news. Third-party sources are allowed when the item clearly affects Microsoft products, Microsoft cloud services, Microsoft security customers, or Microsoft security positioning.

## Implementation constraints

Do not hardcode the source list as final. Implement the source layer so additional Microsoft-relevant sources can be added later with minimal changes. Use source metadata and relevance classification to decide whether an item belongs in the marketing digest.

## Extending sources

Sources are defined in `collector/src/source_registry.py` with metadata:
- `source_type`
- `owner`
- `confidence` (`official_microsoft | official_government | trusted_security_vendor | reputable_news | community | unverified`)
- parser functions (`fetch_index`, `enrich_detail`)

To add a new Microsoft-relevant source:
1. Add a source module under `collector/src/sources/`.
2. Return normalized fields used by `ingest_detail`.
3. Register the source in `SOURCE_DEFINITIONS`.
4. Set `owner` and `confidence`.
5. Ensure Microsoft relevance is determined by classifier fields:
   - `microsoft_relevant`
   - `microsoft_relevance_reason`
   - `affected_microsoft_products`

Third-party sources must default to stricter publication guardrails and usually `requires_review`.

## Digest API time filtering

The API uses internal collector timestamps for time-window filtering.

| Mode | Timestamp field |
|---|---|
| `changed` | `last_changed_at` |
| `new` | `first_seen_at` |
| `seen` | `last_seen_at` |
| `new_or_changed` | `first_seen_at OR last_changed_at` |

Examples:

```bash
curl "http://localhost:8088/digest?hours=48&time_mode=seen&security_only=false&ga_only=false&limit=1000"
curl "http://localhost:8088/digest?hours=48&time_mode=changed&security_only=false&ga_only=false&limit=1000"
```

`published_at` and `updated_at` are source-provided text fields and are not used as the primary API time filters.
