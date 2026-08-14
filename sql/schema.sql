-- ============================================================
-- Economic Release Calendar — Database Schema
-- ============================================================

-- Table 1: NSO Sources (metadata)
CREATE TABLE IF NOT EXISTS nso_sources (
    id          SERIAL PRIMARY KEY,
    code        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    country     TEXT NOT NULL,
    feed_type   TEXT NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE
);

-- Table 2: NSO Releases
CREATE TABLE IF NOT EXISTS nso_releases (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id        INTEGER NOT NULL REFERENCES nso_sources(id),
    title            TEXT NOT NULL,
    release_dt       TIMESTAMPTZ NOT NULL,
    url              TEXT,
    reference_period TEXT,
    source_uid       TEXT NOT NULL UNIQUE,
    first_seen       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nso_dt ON nso_releases (release_dt);
CREATE INDEX IF NOT EXISTS idx_nso_source ON nso_releases (source_id);
CREATE INDEX IF NOT EXISTS idx_nso_title_fts ON nso_releases USING gin (to_tsvector('english', title));

-- Table 3: ForexFactory Releases
CREATE TABLE IF NOT EXISTS ff_releases (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title            TEXT NOT NULL,
    release_dt       TIMESTAMPTZ NOT NULL,
    release_dt_orig  TEXT,
    impact           TEXT NOT NULL,
    currency         TEXT NOT NULL DEFAULT 'EUR',
    actual           TEXT,
    forecast         TEXT,
    previous         TEXT,
    source_uid       TEXT NOT NULL UNIQUE,
    first_seen       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ff_dt ON ff_releases (release_dt);
CREATE INDEX IF NOT EXISTS idx_ff_impact ON ff_releases (impact);
CREATE INDEX IF NOT EXISTS idx_ff_title_fts ON ff_releases USING gin (to_tsvector('english', title));

-- Unified View
CREATE OR REPLACE VIEW all_releases AS
SELECT
    r.id,
    'nso' AS source_type,
    s.code AS source_code,
    s.name AS source_name,
    s.country AS source_country,
    r.title,
    r.release_dt,
    NULL::TEXT AS impact,
    NULL::TEXT AS actual,
    NULL::TEXT AS forecast,
    NULL::TEXT AS previous,
    r.reference_period,
    r.url
FROM nso_releases r
JOIN nso_sources s ON r.source_id = s.id
UNION ALL
SELECT
    f.id,
    'forexfactory' AS source_type,
    'forexfactory' AS source_code,
    'ForexFactory' AS source_name,
    'EUR' AS source_country,
    f.title,
    f.release_dt,
    f.impact,
    f.actual,
    f.forecast,
    f.previous,
    NULL::TEXT AS reference_period,
    NULL::TEXT AS url
FROM ff_releases f;
