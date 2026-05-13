from html import escape

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from .config import DEFAULT_GA_ONLY
from .db import init_db, query_events
from .digest import build_digest, build_marketing_digest

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
    return {"items": query_events(since_iso=since, security_only=security_only, ga_only=ga_only, limit=limit)}


@app.get("/digest")
def digest(
    hours: int = Query(24, ge=1, le=168),
    security_only: bool = Query(True),
    ga_only: bool = Query(DEFAULT_GA_ONLY),
    limit: int = Query(200, ge=1, le=500),
):
    return build_digest(hours=hours, security_only=security_only, ga_only=ga_only, limit=limit)


@app.get("/digest/marketing")
def digest_marketing(
    hours: int = Query(24, ge=1, le=168),
    ga_only: bool = Query(False),
    limit: int = Query(300, ge=1, le=1000),
):
    return build_marketing_digest(hours=hours, ga_only=ga_only, limit=limit)


@app.get("/events/web", response_class=HTMLResponse)
def events_web(
    since: str | None = Query(None, description="ISO8601 timestamp"),
    security_only: bool = Query(False),
    ga_only: bool = Query(DEFAULT_GA_ONLY),
    limit: int = Query(100, ge=1, le=500),
):
    items = query_events(since_iso=since, security_only=security_only, ga_only=ga_only, limit=limit)

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
