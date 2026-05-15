import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

from starlette.requests import Request

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.api import digest
from src import db


def _insert_event(conn, event_id: str, first_seen, last_seen, last_changed, release_stage="Preview", security_relevant=0, published_at=None, updated_at=None):
    conn.execute(
        """
        INSERT INTO events (
          event_id, content_hash, change_type, source, source_uid, source_url,
          title, release_stage, security_relevant, category, raw_json,
          first_seen_at, last_seen_at, last_changed_at, published_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (event_id, f"h-{event_id}", "CHANGED", "test_source", event_id, "https://example.com", event_id, release_stage, security_relevant, "Other", "{}", first_seen.isoformat(), last_seen.isoformat(), last_changed.isoformat(), published_at, updated_at),
    )


def _make_request(path: str):
    return Request({"type": "http", "method": "GET", "path": "/digest", "query_string": path.encode("utf-8"), "headers": []})


def setup_function(_):
    db.IS_POSTGRES = False
    db.DB_PATH = Path("/tmp/test_events.db")
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()
    db.init_db()


def test_hours_windows_and_limit_order():
    now = datetime.now(timezone.utc)
    with db.get_conn() as conn:
        _insert_event(conn, "e12", now - timedelta(hours=12), now - timedelta(hours=12), now - timedelta(hours=12))
        _insert_event(conn, "e36", now - timedelta(hours=36), now - timedelta(hours=36), now - timedelta(hours=36))
        _insert_event(conn, "e60", now - timedelta(hours=60), now - timedelta(hours=60), now - timedelta(hours=60))
        for i in range(10):
            _insert_event(conn, f"inside-{i}", now - timedelta(hours=2), now - timedelta(hours=2), now - timedelta(hours=2))
            _insert_event(conn, f"outside-{i}", now - timedelta(hours=80), now - timedelta(hours=80), now - timedelta(hours=80))
        conn.commit()

    r24 = digest(_make_request("hours=24&time_mode=seen&ga_only=false&security_only=false&limit=1000"))
    r48 = digest(_make_request("hours=48&time_mode=seen&ga_only=false&security_only=false&limit=1000"))
    r72 = digest(_make_request("hours=72&time_mode=seen&ga_only=false&security_only=false&limit=1000"))
    assert r24["matched_count"] == 11
    assert r48["matched_count"] == 12
    assert r72["matched_count"] == 13

    limited = digest(_make_request("hours=24&time_mode=seen&ga_only=false&security_only=false&limit=5"))
    assert limited["matched_count"] == 11
    assert limited["returned_count"] == 5


def test_time_modes_and_boolean_parsing_and_invalid_values():
    now = datetime.now(timezone.utc)
    with db.get_conn() as conn:
        _insert_event(conn, "seen-only", now - timedelta(days=10), now - timedelta(hours=1), now - timedelta(days=10), published_at=None, updated_at=None)
        _insert_event(conn, "changed-only", now - timedelta(days=10), now - timedelta(hours=1), now - timedelta(hours=1), security_relevant=1)
        _insert_event(conn, "new-only", now - timedelta(hours=1), now - timedelta(hours=1), now - timedelta(days=10), release_stage="GA")
        conn.commit()

    seen = digest(_make_request("hours=24&time_mode=seen&ga_only=false&security_only=false&limit=1000"))
    ids = {i["event_id"] for i in seen["items"]}
    assert {"seen-only", "changed-only", "new-only"}.issubset(ids)

    changed = digest(_make_request("hours=24&time_mode=changed&ga_only=false&security_only=false&limit=1000"))
    assert {i["event_id"] for i in changed["items"]} == {"changed-only"}

    new = digest(_make_request("hours=24&time_mode=new&ga_only=false&security_only=false&limit=1000"))
    assert {i["event_id"] for i in new["items"]} == {"new-only"}

    nocut = digest(_make_request("hours=24&time_mode=seen&security_only=false&ga_only=false"))
    assert nocut["matched_count"] >= 3

    sec_ga = digest(_make_request("hours=24&time_mode=seen&security_only=true&ga_only=true"))
    assert sec_ga["matched_count"] == 0

    from fastapi import HTTPException

    try:
        digest(_make_request("security_only=maybe"))
        assert False
    except HTTPException as exc:
        assert exc.status_code == 400

    try:
        digest(_make_request("ga_only=banana"))
        assert False
    except HTTPException as exc:
        assert exc.status_code == 400
