import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path("/app/data/events.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_POSTGRES = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")


def get_conn():
    if IS_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        if IS_POSTGRES:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                  event_id TEXT PRIMARY KEY,
                  content_hash TEXT NOT NULL,
                  change_type TEXT NOT NULL,
                  source TEXT NOT NULL,
                  source_uid TEXT NOT NULL,
                  source_url TEXT NOT NULL,
                  title TEXT NOT NULL,
                  summary TEXT,
                  product TEXT,
                  tags TEXT,
                  release_stage TEXT,
                  published_at TEXT,
                  updated_at TEXT,
                  security_relevant INTEGER,
                  security_reason TEXT,
                  category TEXT,
                  impact TEXT,
                  recommended_action TEXT,
                  microsoft_relevant INTEGER,
                  microsoft_relevance_reason TEXT,
                  affected_microsoft_products TEXT,
                  source_confidence TEXT,
                  publication_guardrail TEXT,
                  raw_json TEXT,
                  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  last_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_published ON events(published_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_stage ON events(release_stage);")
            conn.commit()
            return

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
              event_id TEXT PRIMARY KEY,
              content_hash TEXT NOT NULL,
              change_type TEXT NOT NULL,         -- NEW|CHANGED|UNCHANGED (stored on last ingest)
              source TEXT NOT NULL,
              source_uid TEXT NOT NULL,          -- stable per-source id if available
              source_url TEXT NOT NULL,
              title TEXT NOT NULL,
              summary TEXT,
              product TEXT,
              tags TEXT,
              release_stage TEXT,                -- GA|Preview|Planned|Retirement|Unknown
              published_at TEXT,
              updated_at TEXT,
              security_relevant INTEGER,
              security_reason TEXT,
              category TEXT,
              impact TEXT,
              recommended_action TEXT,
              microsoft_relevant INTEGER,
                  microsoft_relevance_reason TEXT,
                  affected_microsoft_products TEXT,
                  source_confidence TEXT,
                  publication_guardrail TEXT,
                  raw_json TEXT,
              first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
              last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
              last_changed_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_published ON events(published_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_stage ON events(release_stage);")


def get_event(event_id: str):
    with get_conn() as conn:
        if IS_POSTGRES:
            r = conn.execute("SELECT * FROM events WHERE event_id = %s", (event_id,)).fetchone()
            return dict(r) if r else None

        r = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
        return dict(r) if r else None


def upsert_event(event: dict):
    with get_conn() as conn:
        if IS_POSTGRES:
            existing = conn.execute("SELECT content_hash FROM events WHERE event_id = %s", (event["event_id"],)).fetchone()

            if existing is None:
                change_type = "NEW"
                last_changed_expr = "NOW()"
            elif existing["content_hash"] != event["content_hash"]:
                change_type = "CHANGED"
                last_changed_expr = "NOW()"
            else:
                change_type = "UNCHANGED"
                last_changed_expr = "events.last_changed_at"

            conn.execute(
                f"""
                INSERT INTO events (
                  event_id, content_hash, change_type,
                  source, source_uid, source_url,
                  title, summary, product, tags,
                  release_stage, published_at, updated_at,
                  security_relevant, security_reason, category,
                  impact, recommended_action,
                  microsoft_relevant, microsoft_relevance_reason, affected_microsoft_products, source_confidence, publication_guardrail,
                  raw_json, last_seen_at, last_changed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT(event_id) DO UPDATE SET
                  content_hash=EXCLUDED.content_hash,
                  change_type=%s,
                  title=EXCLUDED.title,
                  summary=EXCLUDED.summary,
                  product=EXCLUDED.product,
                  tags=EXCLUDED.tags,
                  release_stage=EXCLUDED.release_stage,
                  published_at=EXCLUDED.published_at,
                  updated_at=EXCLUDED.updated_at,
                  security_relevant=EXCLUDED.security_relevant,
                  security_reason=EXCLUDED.security_reason,
                  category=EXCLUDED.category,
                  impact=EXCLUDED.impact,
                  recommended_action=EXCLUDED.recommended_action,
                  microsoft_relevant=EXCLUDED.microsoft_relevant,
                  microsoft_relevance_reason=EXCLUDED.microsoft_relevance_reason,
                  affected_microsoft_products=EXCLUDED.affected_microsoft_products,
                  source_confidence=EXCLUDED.source_confidence,
                  publication_guardrail=EXCLUDED.publication_guardrail,
                  raw_json=EXCLUDED.raw_json,
                  last_seen_at=NOW(),
                  last_changed_at={last_changed_expr};
                """,
                (
                    event["event_id"],
                    event["content_hash"],
                    change_type,
                    event["source"],
                    event.get("source_uid", ""),
                    event["source_url"],
                    event["title"],
                    event.get("summary"),
                    event.get("product"),
                    json.dumps(event.get("tags", [])),
                    event.get("release_stage", "Unknown"),
                    event.get("published_at"),
                    event.get("updated_at"),
                    1 if event.get("security_relevant") else 0,
                    event.get("security_reason"),
                    event.get("category", "Other"),
                    event.get("impact", "Unknown"),
                    event.get("recommended_action"),
                    1 if event.get("microsoft_relevant") else 0,
                    event.get("microsoft_relevance_reason"),
                    json.dumps(event.get("affected_microsoft_products", [])),
                    event.get("source_confidence"),
                    event.get("publication_guardrail"),
                    json.dumps(event.get("raw", {})),
                    change_type,
                ),
            )
            conn.commit()
            return change_type

        existing = conn.execute("SELECT content_hash FROM events WHERE event_id = ?", (event["event_id"],)).fetchone()

        if existing is None:
            change_type = "NEW"
            last_changed_at_sql = "datetime('now')"
        else:
            if existing["content_hash"] != event["content_hash"]:
                change_type = "CHANGED"
                last_changed_at_sql = "datetime('now')"
            else:
                change_type = "UNCHANGED"
                last_changed_at_sql = "last_changed_at"

        conn.execute(
            f"""
            INSERT INTO events (
              event_id, content_hash, change_type,
              source, source_uid, source_url,
              title, summary, product, tags,
              release_stage, published_at, updated_at,
              security_relevant, security_reason, category,
              impact, recommended_action,
              microsoft_relevant, microsoft_relevance_reason, affected_microsoft_products, source_confidence, publication_guardrail,
              raw_json, last_seen_at, last_changed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(event_id) DO UPDATE SET
              content_hash=excluded.content_hash,
              change_type='{change_type}',
              title=excluded.title,
              summary=excluded.summary,
              product=excluded.product,
              tags=excluded.tags,
              release_stage=excluded.release_stage,
              published_at=excluded.published_at,
              updated_at=excluded.updated_at,
              security_relevant=excluded.security_relevant,
              security_reason=excluded.security_reason,
              category=excluded.category,
              impact=excluded.impact,
              recommended_action=excluded.recommended_action,
              microsoft_relevant=excluded.microsoft_relevant,
              microsoft_relevance_reason=excluded.microsoft_relevance_reason,
              affected_microsoft_products=excluded.affected_microsoft_products,
              source_confidence=excluded.source_confidence,
              publication_guardrail=excluded.publication_guardrail,
              raw_json=excluded.raw_json,
              last_seen_at=datetime('now'),
              last_changed_at={last_changed_at_sql};
            """,
            (
                event["event_id"],
                event["content_hash"],
                change_type,
                event["source"],
                event.get("source_uid", ""),
                event["source_url"],
                event["title"],
                event.get("summary"),
                event.get("product"),
                json.dumps(event.get("tags", [])),
                event.get("release_stage", "Unknown"),
                event.get("published_at"),
                event.get("updated_at"),
                1 if event.get("security_relevant") else 0,
                event.get("security_reason"),
                event.get("category", "Other"),
                event.get("impact", "Unknown"),
                event.get("recommended_action"),
                1 if event.get("microsoft_relevant") else 0,
                event.get("microsoft_relevance_reason"),
                json.dumps(event.get("affected_microsoft_products", [])),
                event.get("source_confidence"),
                event.get("publication_guardrail"),
                json.dumps(event.get("raw", {})),
            ),
        )

        return change_type


def query_events(since_iso: str | None = None, security_only: bool = False, ga_only: bool = False, limit: int = 100):
    if IS_POSTGRES:
        q = "SELECT * FROM events WHERE 1=1"
        args = []
        if since_iso:
            q += " AND (published_at >= %s OR updated_at >= %s OR last_changed_at::text >= %s)"
            args += [since_iso, since_iso, since_iso]
        if security_only:
            q += " AND security_relevant = 1"
        if ga_only:
            q += " AND release_stage = 'GA'"
        q += " ORDER BY COALESCE(updated_at, published_at, last_changed_at::text) DESC LIMIT %s"
        args.append(limit)

        with get_conn() as conn:
            rows = conn.execute(q, args).fetchall()
            return [dict(r) for r in rows]

    q = "SELECT * FROM events WHERE 1=1"
    args = []
    if since_iso:
        q += " AND (published_at >= ? OR updated_at >= ? OR last_changed_at >= ?)"
        args += [since_iso, since_iso, since_iso]
    if security_only:
        q += " AND security_relevant = 1"
    if ga_only:
        q += " AND release_stage = 'GA'"
    q += " ORDER BY COALESCE(updated_at, published_at, last_changed_at) DESC LIMIT ?"
    args.append(limit)

    with get_conn() as conn:
        rows = conn.execute(q, args).fetchall()
        return [dict(r) for r in rows]
