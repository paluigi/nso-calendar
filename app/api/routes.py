"""FastAPI routes — calendar page and filtered release cards."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone
from calendar import monthrange

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


UNION_SQL = """
    SELECT * FROM (
        SELECT r.id AS id, 'nso' AS source_type, s.code AS source_code, s.name AS source_name,
               r.title AS title, r.release_dt AS release_dt, NULL::TEXT AS impact,
               NULL::TEXT AS actual, NULL::TEXT AS forecast,
               NULL::TEXT AS previous, r.reference_period AS reference_period, r.url AS url
        FROM nso_releases r JOIN nso_sources s ON r.source_id = s.id
        UNION ALL
        SELECT id, 'forexfactory' AS source_type, 'forexfactory' AS source_code,
               'ForexFactory' AS source_name, title, release_dt, impact,
               actual, forecast, previous, NULL::TEXT AS reference_period,
               NULL::TEXT AS url
        FROM ff_releases
    ) AS all_r WHERE 1=1
"""


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = (year * 12 + (month - 1)) + delta
    return total // 12, total % 12 + 1


def _resolve_defaults(date_from: date | None, date_to: date | None, q: str | None) -> tuple[date | None, date | None]:
    """Apply default date range logic."""
    today = date.today()
    if date_from is None and date_to is None and not q:
        # No filters → current month
        date_from = today.replace(day=1)
        date_to = date(today.year, today.month, monthrange(today.year, today.month)[1])
    elif date_from is None and q:
        # Text search active → start from first day of previous month
        prev = _shift_month(today.year, today.month, -1)
        date_from = date(prev[0], prev[1], 1)
    return date_from, date_to


def _build_filter_sql(source: str | None, date_from: date | None, date_to: date | None, q: str | None) -> tuple[str, dict]:
    """Build WHERE clause + params dict. date_to is treated as inclusive (+1 day in Python)."""
    sql = UNION_SQL
    params: dict = {}

    if source:
        sql += " AND source_code = :source"
        params["source"] = source
    if date_from:
        sql += " AND release_dt >= :date_from"
        params["date_from"] = date_from
    if date_to:
        # Add 1 day in Python to make date_to inclusive
        sql += " AND release_dt < :date_to_exclusive"
        params["date_to_exclusive"] = date_to + timedelta(days=1)
    if q:
        sql += " AND title ILIKE :q"
        params["q"] = f"%{q}%"

    return sql, params


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main calendar page."""
    today = date.today()
    default_date_from = today.replace(day=1)
    default_date_to = date(today.year, today.month, monthrange(today.year, today.month)[1])

    return templates.TemplateResponse(request, "index.html", {
        "default_date_from": default_date_from.isoformat(),
        "default_date_to": default_date_to.isoformat(),
    })


@router.get("/api/releases", response_class=HTMLResponse)
async def get_releases(
    request: Request,
    source: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Filtered release cards (UNION of NSO + ForexFactory tables)."""
    date_from, date_to = _resolve_defaults(date_from, date_to, q)
    sql, params = _build_filter_sql(source, date_from, date_to, q)
    sql += " ORDER BY release_dt ASC LIMIT 500"

    result = await db.execute(text(sql), params)
    releases = result.fetchall()

    return templates.TemplateResponse(request, "partials/_releases.html", {
        "releases": releases,
        "now": datetime.now(timezone.utc),
    })


@router.get("/api/releases/export")
async def export_releases(
    source: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """CSV export of filtered releases."""
    date_from, date_to = _resolve_defaults(date_from, date_to, q)
    sql, params = _build_filter_sql(source, date_from, date_to, q)
    sql += " ORDER BY release_dt ASC LIMIT 5000"

    result = await db.execute(text(sql), params)
    releases = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date (UTC)", "Source", "Title", "Impact", "Actual", "Forecast", "Previous", "Ref. Period"])
    for r in releases:
        writer.writerow([
            r.release_dt.strftime("%Y-%m-%d %H:%M") if r.release_dt else "",
            r.source_name,
            r.title,
            r.impact or "",
            r.actual or "",
            r.forecast or "",
            r.previous or "",
            r.reference_period or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=releases.csv"},
    )
