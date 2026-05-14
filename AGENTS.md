# Codex task: Fix API/web result retrieval versus database state

## Context

This repository contains a Microsoft Azure/M365 change intelligence collector with a PostgreSQL-backed event store and web/API endpoints such as `/digest`.

Database inspection confirms that relevant events are stored in PostgreSQL, but the web/API layer does not return the same results.

Observed database state:

- `events` table contains events from:
  - `graph_message_center`
  - `defender_whatsnew`
  - `entra_whatsnew`
  - `intune_whatsnew`

The table includes internal collector timestamps:

- `first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `last_changed_at TIMESTAMPTZ NOT NULL DEFAULT now()`

The source timestamp fields are unreliable for filtering:

- `published_at TEXT`
- `updated_at TEXT`

Several sources have empty or NULL `published_at` and `updated_at`, so these fields must not be used as primary API time filters.

## Problem

The API/web layer does not reliably return the events that are visible in the database.

Examples:

- Events can be queried directly from PostgreSQL using `last_seen_at`, `first_seen_at`, and `last_changed_at`.
- The API returns fewer or no results for equivalent time windows.
- The `hours` parameter does not appear to work correctly beyond 24 hours.
- Calling with `hours=48` does not return items that are visible in the database for the past 48 hours.
- Query parameters may be ignored, incorrectly parsed, capped, overwritten by defaults, or applied to the wrong timestamp fields.
- Boolean query parameters such as `ga_only=false` and `security_only=false` may be parsed incorrectly as truthy strings.
- API filtering may use source fields such as `published_at` or `updated_at`, which are text fields and often empty.

## Goal

Fix the overall API result retrieval logic so that web/API responses match PostgreSQL state for equivalent filters.

This is not limited to a single endpoint. Review all API endpoints that expose event or digest data and ensure they use the correct database fields, query parameters, filter order, and limits.

## Required investigation

Inspect the current implementation and identify:

1. Where `/digest` and related endpoints are defined.
2. Where query parameters are parsed.
3. Whether `hours` is:
   - ignored;
   - capped at 24;
   - parsed as string;
   - overwritten by a default;
   - rejected silently;
   - applied after limiting;
   - applied to the wrong timestamp field.
4. Whether boolean query parameters are parsed safely.
5. Whether the API queries `published_at` or `updated_at` instead of internal timestamp fields.
6. Whether results are limited before filtering.
7. Whether filters are applied in Python after a too-small database query.
8. Whether `limit` defaults are hiding valid results.
9. Whether sorting causes older or irrelevant records to be selected before filtering.
10. Whether API and collector use the same database/schema.
11. Whether the web container points to a different database than the one inspected manually.
12. Whether timezone-aware UTC datetime handling is consistent.

## Critical requirement: database/API consistency

For every supported API filter, the API result count must match the equivalent SQL count, except where an explicit `limit` is applied.

Example:

```sql
SELECT COUNT(*)
FROM events
WHERE last_seen_at >= NOW() - INTERVAL '48 hours';
```

must align with:

```http
GET /digest?hours=48&time_mode=seen&ga_only=false&security_only=false&limit=1000
```

If the SQL count is 119 and the API limit is 1000, the API count must be 119.

## Time filtering model

Use internal collector timestamps for API time filtering.

Do not use `published_at` or `updated_at` as the primary API time-window fields.

Supported time modes:

| time_mode | Field / logic |
|---|---|
| `changed` | `last_changed_at >= cutoff` |
| `new` | `first_seen_at >= cutoff` |
| `seen` | `last_seen_at >= cutoff` |
| `new_or_changed` | `first_seen_at >= cutoff OR last_changed_at >= cutoff` |

Default behavior:

```text
time_mode=changed
```

This preserves a strict change-digest behavior and avoids returning old items every collector run.

However, `time_mode=seen` must work for troubleshooting/source validation.

## Hours parameter

The `hours` parameter must be fully functional.

Requirements:

- Parse `hours` as integer.
- Default to existing default or `24`.
- Allow at least values from `1` to `168`.
- Do not silently cap to `24`.
- Do not ignore values greater than `24`.
- If the implementation requires a maximum, document it and return HTTP 400 when exceeded.
- Invalid values must return HTTP 400.

Accepted examples:

```http
/digest?hours=1
/digest?hours=24
/digest?hours=48
/digest?hours=72
/digest?hours=168
```

Expected cutoff logic:

```python
cutoff = now_utc - timedelta(hours=hours)
```

The response must include the computed cutoff.

## Query parameter parsing

Implement strict parsing helpers if not already present.

### Integer parsing

For `hours` and `limit`:

- Convert to integer.
- Reject non-integer values.
- Reject zero or negative values.
- Return HTTP 400 with clear error details.

### Boolean parsing

Do not rely on Python truthiness for strings.

This is wrong:

```python
bool("false") == True
```

Accepted true values:

```text
true, 1, yes, on
```

Accepted false values:

```text
false, 0, no, off
```

Parameters that need strict boolean parsing:

- `security_only`
- `ga_only`
- `marketing_only`
- `include_review_required`
- `debug`, if present

Invalid values must return HTTP 400.

## Required filter order

Apply filters in this order:

1. Time-window filter using internal timestamp field and `time_mode`
2. `security_only`
3. `ga_only`
4. `marketing_only`, if present
5. `include_review_required`, if present
6. Sorting
7. `limit`

Important: do not apply `limit` before filters.

Bad pattern:

```python
events = query.limit(limit).all()
events = filter_by_time(events)
```

Good pattern:

```python
query = query.filter(time_condition)
query = query.filter(optional_filters)
query = query.order_by(...)
query = query.limit(limit)
```

## Sorting rules

Sort by the relevant timestamp for the selected time mode.

| time_mode | Sort |
|---|---|
| `changed` | `last_changed_at DESC` |
| `new` | `first_seen_at DESC` |
| `seen` | `last_seen_at DESC` |
| `new_or_changed` | `GREATEST(first_seen_at, last_changed_at) DESC` |

If the database abstraction does not support `GREATEST`, perform equivalent logic safely in Python after selecting all candidate records for the requested window.

## Response metadata

All digest/event API responses must expose enough metadata to troubleshoot filtering.

Top-level response must include:

```json
{
  "generated_at": "2026-05-14T19:00:00Z",
  "window_hours": 48,
  "time_mode": "seen",
  "cutoff": "2026-05-12T19:00:00Z",
  "security_only": false,
  "ga_only": false,
  "marketing_only": false,
  "limit": 1000,
  "count": 119
}
```

Each item must include:

```json
{
  "effective_at": "2026-05-14T07:00:16Z",
  "effective_at_source": "last_seen_at"
}
```

Effective timestamp source:

| time_mode | effective_at_source |
|---|---|
| `changed` | `last_changed_at` |
| `new` | `first_seen_at` |
| `seen` | `last_seen_at` |
| `new_or_changed` | `first_seen_at` or `last_changed_at`, whichever is newer |

## Add API/database diagnostics

Add a debug endpoint or debug mode.

Preferred:

```http
GET /digest/debug?hours=48&ga_only=false&security_only=false
```

The debug output must show counts by source for each stage.

Required structure:

```json
{
  "generated_at": "2026-05-14T19:00:00Z",
  "window_hours": 48,
  "cutoff": "2026-05-12T19:00:00Z",
  "database_connection": {
    "host": "ms-changes-postgres",
    "database": "collector"
  },
  "time_modes": {
    "changed": {
      "total": 0,
      "by_source": {}
    },
    "new": {
      "total": 0,
      "by_source": {}
    },
    "seen": {
      "total": 119,
      "by_source": {
        "graph_message_center": 100,
        "defender_whatsnew": 12,
        "entra_whatsnew": 6,
        "intune_whatsnew": 1
      }
    },
    "new_or_changed": {
      "total": 0,
      "by_source": {}
    }
  },
  "selected_mode_pipeline": {
    "before_filters": {
      "total": 119,
      "by_source": {}
    },
    "after_time_filter": {
      "total": 119,
      "by_source": {}
    },
    "after_security_filter": {
      "total": 119,
      "by_source": {}
    },
    "after_ga_filter": {
      "total": 119,
      "by_source": {}
    },
    "after_marketing_filter": {
      "total": 119,
      "by_source": {}
    },
    "after_limit": {
      "total": 119,
      "by_source": {}
    }
  }
}
```

The exact structure can differ, but it must show:

- database used by the API;
- cutoff timestamp;
- selected filters;
- counts before and after each filter;
- counts grouped by source.

## Verify API uses the same database as manual psql

Add logging or debug output that confirms:

- database host;
- database name;
- database user, if safe;
- current database time;
- application UTC time;
- count of total events.

Do not expose passwords or secrets.

Example:

```json
{
  "database": {
    "host": "ms-changes-postgres",
    "name": "collector",
    "server_now": "2026-05-14T19:00:00Z",
    "total_events": 119
  }
}
```

This prevents troubleshooting the wrong database/container.

## Manual SQL equivalence checks

The API must be validated against these SQL queries.

### changed

```sql
SELECT source, COUNT(*)
FROM events
WHERE last_changed_at >= NOW() - INTERVAL '48 hours'
GROUP BY source
ORDER BY COUNT(*) DESC;
```

Equivalent API:

```http
GET /digest?hours=48&time_mode=changed&ga_only=false&security_only=false&limit=1000
```

### new

```sql
SELECT source, COUNT(*)
FROM events
WHERE first_seen_at >= NOW() - INTERVAL '48 hours'
GROUP BY source
ORDER BY COUNT(*) DESC;
```

Equivalent API:

```http
GET /digest?hours=48&time_mode=new&ga_only=false&security_only=false&limit=1000
```

### seen

```sql
SELECT source, COUNT(*)
FROM events
WHERE last_seen_at >= NOW() - INTERVAL '48 hours'
GROUP BY source
ORDER BY COUNT(*) DESC;
```

Equivalent API:

```http
GET /digest?hours=48&time_mode=seen&ga_only=false&security_only=false&limit=1000
```

### new_or_changed

```sql
SELECT source, COUNT(*)
FROM events
WHERE first_seen_at >= NOW() - INTERVAL '48 hours'
   OR last_changed_at >= NOW() - INTERVAL '48 hours'
GROUP BY source
ORDER BY COUNT(*) DESC;
```

Equivalent API:

```http
GET /digest?hours=48&time_mode=new_or_changed&ga_only=false&security_only=false&limit=1000
```

## Tests required

Add or update tests for API result consistency.

### Test: hours is not capped at 24

Create events with timestamps:

- now - 12 hours
- now - 36 hours
- now - 60 hours

Expected:

- `hours=24` returns only 12h event.
- `hours=48` returns 12h and 36h events.
- `hours=72` returns 12h, 36h, and 60h events.

### Test: seen mode uses last_seen_at

Fixture:

```text
first_seen_at = now - 10 days
last_changed_at = now - 10 days
last_seen_at = now - 1 hour
```

Expected:

- included in `time_mode=seen&hours=24`
- excluded from `time_mode=changed&hours=24`
- excluded from `time_mode=new&hours=24`
- excluded from `time_mode=new_or_changed&hours=24`

### Test: changed mode uses last_changed_at

Fixture:

```text
first_seen_at = now - 10 days
last_changed_at = now - 1 hour
last_seen_at = now - 1 hour
```

Expected:

- included in `changed`
- included in `seen`
- included in `new_or_changed`
- excluded from `new`

### Test: new mode uses first_seen_at

Fixture:

```text
first_seen_at = now - 1 hour
last_changed_at = now - 10 days
last_seen_at = now - 1 hour
```

Expected:

- included in `new`
- included in `seen`
- included in `new_or_changed`
- excluded from `changed`

### Test: boolean parsing

Validate:

```http
/digest?security_only=false&ga_only=false
```

does not apply security or GA filtering.

Validate:

```http
/digest?security_only=true&ga_only=true
```

does apply both filters.

Validate invalid values return HTTP 400:

```http
/digest?security_only=maybe
/digest?ga_only=banana
```

### Test: limit applied last

Create 20 events, 10 within the time window and 10 outside.

Request:

```http
/digest?hours=24&limit=5
```

Expected:

- filter to 10 valid events first;
- return 5 due to limit;
- count metadata should clearly indicate final count or include both `matched_count` and `returned_count`.

Preferred metadata:

```json
{
  "matched_count": 10,
  "returned_count": 5
}
```

## Response count semantics

Clarify and implement count semantics.

Preferred:

```json
{
  "matched_count": 119,
  "returned_count": 100,
  "limit": 100
}
```

If existing API only has `count`, ensure it reflects returned items and add `matched_count` to avoid ambiguity.

## Backward compatibility

Do not break existing consumers.

If existing clients expect `count`, keep `count`.

Add new fields instead of removing old ones:

- `matched_count`
- `returned_count`
- `time_mode`
- `cutoff`
- `effective_at`
- `effective_at_source`

## Documentation update

Update README with:

```markdown
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
```

## Acceptance criteria

This task is complete only when all of the following are true:

1. API results match equivalent PostgreSQL queries for:
   - `changed`
   - `new`
   - `seen`
   - `new_or_changed`

2. `hours=48` works and is not silently capped at 24.

3. `hours=72` and `hours=168` work unless explicitly rejected with HTTP 400.

4. `security_only=false` and `ga_only=false` are parsed as false, not truthy strings.

5. `limit` is applied after filtering, not before.

6. The API does not use `published_at` or `updated_at` as the main time filter.

7. API response includes:
   - `window_hours`
   - `time_mode`
   - `cutoff`
   - `matched_count`
   - `returned_count`
   - `limit`

8. Each item includes:
   - `effective_at`
   - `effective_at_source`

9. `/digest/debug` or equivalent debug mode proves why items are included or excluded.

10. The debug output confirms the API is connected to the same database being inspected manually.

11. Tests cover:
   - 24h versus 48h versus 72h windows;
   - all time modes;
   - boolean parsing;
   - limit applied after filtering;
   - records with empty `published_at` and `updated_at`.

## Final instruction

Do not only patch the visible symptom.

Trace the full request path:

```text
HTTP query parameters
  → parsing/validation
  → computed cutoff
  → database query construction
  → filter order
  → sorting
  → limit
  → response serialization
```

Then implement the smallest clean change set that makes API/web results consistent with PostgreSQL.
