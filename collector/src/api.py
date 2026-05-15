from html import escape
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from .config import DEFAULT_GA_ONLY
from .db import IS_POSTGRES, DATABASE_URL, get_conn, init_db, query_events
from .digest import build_digest

app = FastAPI(title="Microsoft Changes Collector", version="1.0")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/events")
def events(
    since: str | None = Query(None, description="ISO8601 timestamp"),
    security_only: bool = Query(False),
    ga_only: bool = Query(DEFAULT_GA_ONLY),
    limit: int = Query(100, ge=1, le=500),
):
    cutoff = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
    return {"items": query_events(cutoff=cutoff, time_mode="changed", security_only=security_only, ga_only=ga_only, limit=limit)}


@app.get("/digest")
def digest(request: Request):
    qp = request.query_params
    hours = parse_int("hours", qp.get("hours"), 24, 1, 168)
    limit = parse_int("limit", qp.get("limit"), 200, 1, 10000)
    security_only = parse_bool("security_only", qp.get("security_only"), False)
    ga_only = parse_bool("ga_only", qp.get("ga_only"), DEFAULT_GA_ONLY)
    marketing_only = parse_bool("marketing_only", qp.get("marketing_only"), False)
    include_review_required = parse_bool("include_review_required", qp.get("include_review_required"), True)
    time_mode = qp.get("time_mode", "changed")
    if time_mode not in {"changed", "new", "seen", "new_or_changed"}:
        raise HTTPException(status_code=400, detail=f"Invalid time_mode: {time_mode}")
    return build_digest(hours=hours, security_only=security_only, ga_only=ga_only, marketing_only=marketing_only, include_review_required=include_review_required, limit=limit, time_mode=time_mode)


@app.get("/digest/debug")
def digest_debug(request: Request):
    payload = digest(request)
    with get_conn() as conn:
        total_events = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
        server_now = conn.execute("SELECT NOW() AS now" if IS_POSTGRES else "SELECT datetime('now') AS now").fetchone()["now"]
    db_name = DATABASE_URL.split("/")[-1].split("?")[0] if DATABASE_URL else str("sqlite")
    db_host = DATABASE_URL.split("@")[1].split("/")[0] if "@" in DATABASE_URL else "local"
    payload["database"] = {
        "host": db_host,
        "name": db_name,
        "server_now": str(server_now),
        "app_now_utc": datetime.now(timezone.utc).isoformat(),
        "total_events": total_events,
    }
    return payload


@app.get("/events/web", response_class=HTMLResponse)
def events_web(
    since: str | None = Query(None, description="ISO8601 timestamp"),
    security_only: bool = Query(False),
    ga_only: bool = Query(DEFAULT_GA_ONLY),
    limit: int = Query(100, ge=1, le=500),
):
    cutoff = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
    items = query_events(cutoff=cutoff, time_mode="changed", security_only=security_only, ga_only=ga_only, limit=limit)

    rows = []
    for it in items:
        title = escape(it.get("title") or "")
        source = escape(it.get("source") or "")
        stage = escape(it.get("release_stage") or "Unknown")
        change_type = escape(it.get("change_type") or "")
        category = escape(it.get("category") or "")
        published_at = escape(it.get("published_at") or "")
        updated_at = escape(it.get("updated_at") or "")
        security = "✅" if it.get("security_relevant") else ""
        url = escape(it.get("source_url") or "")

        rows.append(
            f"""
            <tr>
              <td>{published_at}</td>
              <td>{updated_at}</td>
              <td>{change_type}</td>
              <td>{source}</td>
              <td>{stage}</td>
              <td>{category}</td>
              <td>{security}</td>
              <td><a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{title}</a></td>
            </tr>
            """
        )

    rows_html = "\n".join(rows) if rows else "<tr><td colspan='8'>Geen resultaten</td></tr>"

    html = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Changes overzicht</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
        h1 {{ margin-bottom: 4px; }}
        .meta {{ color: #555; margin-bottom: 20px; }}
        form {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; align-items: end; }}
        label {{ display: flex; flex-direction: column; gap: 6px; font-size: 14px; }}
        input[type='text'], input[type='number'] {{ padding: 6px 8px; min-width: 180px; }}
        .checks {{ display: flex; gap: 12px; align-items: center; }}
        button {{ padding: 8px 12px; cursor: pointer; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
        th {{ background: #f7f7f7; position: sticky; top: 0; }}
        .wrap {{ max-height: 72vh; overflow: auto; border: 1px solid #ddd; }}
      </style>
    </head>
    <body>
      <h1>Database-overzicht van wijzigingen</h1>
      <div class="meta">Deze pagina leest direct uit de interne database. API endpoints blijven beschikbaar op <code>/events</code> en <code>/digest</code>.</div>

      <form method="get" action="/events/web">
        <label>
          Sinds (ISO8601)
          <input type="text" name="since" value="{escape(since or '')}" placeholder="2026-04-01T00:00:00Z" />
        </label>
        <label>
          Limiet
          <input type="number" name="limit" min="1" max="500" value="{limit}" />
        </label>
        <label class="checks"><input type="checkbox" name="security_only" value="true" {"checked" if security_only else ""} /> Security only</label>
        <label class="checks"><input type="checkbox" name="ga_only" value="true" {"checked" if ga_only else ""} /> GA only</label>
        <button type="submit">Filter toepassen</button>
      </form>

      <div class="wrap">
        <table>
          <thead>
            <tr>
              <th>Published</th>
              <th>Updated</th>
              <th>Change</th>
              <th>Source</th>
              <th>Stage</th>
              <th>Category</th>
              <th>Security</th>
              <th>Titel</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </div>
    </body>
    </html>
    """

    return html
def parse_bool(name: str, value: str | None, default: bool) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    if v in {"true", "1", "yes", "on"}:
        return True
    if v in {"false", "0", "no", "off"}:
        return False
    raise HTTPException(status_code=400, detail=f"Invalid boolean for {name}: {value}")


def parse_int(name: str, value: str | None, default: int, min_v: int, max_v: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid integer for {name}: {value}") from exc
    if parsed < min_v or parsed > max_v:
        raise HTTPException(status_code=400, detail=f"{name} must be between {min_v} and {max_v}")
    return parsed
