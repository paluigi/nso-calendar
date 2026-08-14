"""Database upsert operations for NSO and ForexFactory releases."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NSOReleaseRecord, FFReleaseRecord


async def upsert_nso_releases(session: AsyncSession, records: list[NSOReleaseRecord]) -> int:
    """Upsert NSO release records. Returns number of upserted rows."""
    if not records:
        return 0

    count = 0
    for r in records:
        # Look up source_id by code
        result = await session.execute(
            text("SELECT id FROM nso_sources WHERE code = :code"),
            {"code": r.source_code},
        )
        row = result.fetchone()
        if not row:
            logging.warning(f"NSO source '{r.source_code}' not found in nso_sources table, skipping")
            continue

        source_id = row[0]

        await session.execute(
            text("""
                INSERT INTO nso_releases (source_id, title, release_dt, url, reference_period, source_uid)
                VALUES (:source_id, :title, :release_dt, :url, :reference_period, :source_uid)
                ON CONFLICT (source_uid) DO UPDATE SET
                    title           = EXCLUDED.title,
                    url             = EXCLUDED.url,
                    reference_period = EXCLUDED.reference_period,
                    updated_at      = NOW()
            """),
            {
                "source_id": source_id,
                "title": r.title,
                "release_dt": r.release_dt,
                "url": r.url,
                "reference_period": r.reference_period,
                "source_uid": r.source_uid,
            },
        )
        count += 1

    await session.commit()
    return count


async def upsert_ff_releases(session: AsyncSession, records: list[FFReleaseRecord]) -> int:
    """
    Upsert ForexFactory release records. Updates actual/forecast/previous when changed.
    Does NOT delete old records — history is preserved.
    """
    if not records:
        return 0

    count = 0
    for r in records:
        await session.execute(
            text("""
                INSERT INTO ff_releases
                    (title, release_dt, release_dt_orig, impact, currency, actual, forecast, previous, source_uid)
                VALUES
                    (:title, :release_dt, :release_dt_orig, :impact, :currency, :actual, :forecast, :previous, :source_uid)
                ON CONFLICT (source_uid) DO UPDATE SET
                    actual     = COALESCE(EXCLUDED.actual, ff_releases.actual),
                    forecast   = COALESCE(EXCLUDED.forecast, ff_releases.forecast),
                    previous   = COALESCE(EXCLUDED.previous, ff_releases.previous),
                    impact     = EXCLUDED.impact,
                    updated_at = NOW()
            """),
            {
                "title": r.title,
                "release_dt": r.release_dt,
                "release_dt_orig": r.release_dt_orig,
                "impact": r.impact,
                "currency": r.currency,
                "actual": r.actual,
                "forecast": r.forecast,
                "previous": r.previous,
                "source_uid": r.source_uid,
            },
        )
        count += 1

    await session.commit()
    return count
