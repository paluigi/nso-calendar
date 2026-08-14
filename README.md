# Economic Release Calendar

Aggregates scheduled data releases from European NSOs and ForexFactory into a single filterable web calendar.

## Data Sources

| Source | Method | Coverage |
|---|---|---|
| **Eurostat** (EU) | ICS feed | Full year+ |
| **Istat** (IT) | ICS (Google Calendar) | Full year |
| **INE** (ES) | ICS feed | Full year |
| **Destatis** (DE) | HTML scraping (annual calendar, 13 topic facets) | Full year+ |
| **INSEE** (FR) | HTML scraping (embargo calendar) | Rolling 2 weeks |
| **CSO** (IE) | PxStat REST API | Past releases |
| **ForexFactory** | HTML scraping (monthly, EUR-only) | Jun 2026 → +3 months ahead |

## Features

- **Unified calendar**: NSO releases + ForexFactory events in one view
- **Filter** by source, date range, partial text search (case-insensitive)
- **Default view**: current month; text search expands to previous month
- **ForexFactory cards** show impact ratings + actual/forecast/previous values, visually differentiated from NSO cards
- **Weekly auto-update**: every Monday at 07:00 UTC

## Stack

FastAPI · HTMX · Pico CSS · PostgreSQL · Docker

## Quick Start

```bash
# Clone and run
docker compose up --build

# First-time: backfill ForexFactory data (Jun 2026 → now)
docker compose exec app python scripts/backfill_ff.py
```

Then open http://localhost:8000

## Local Development

```bash
# Install deps
uv pip install -e ".[dev]"

# Start PostgreSQL
docker compose up db

# Init database
python scripts/init_db.py

# Backfill ForexFactory
python scripts/backfill_ff.py

# Run app
uvicorn app.main:app --reload
```

## Architecture

```
app/
├── main.py              # FastAPI app + scheduler
├── config.py            # Settings
├── database.py          # SQLAlchemy async
├── models.py            # ORM models + record dataclasses
├── db_ops.py            # Upsert operations
├── scheduler.py         # APScheduler (Monday 07:00 UTC)
├── api/routes.py        # Endpoints + filter logic
├── collectors/
│   ├── base.py
│   ├── ics_collector.py       # Eurostat, Istat, INE
│   ├── destatis_collector.py  # 13 topic facets
│   ├── insee_collector.py     # French embargo calendar
│   ├── cso_collector.py       # PxStat REST API
│   └── forexfactory_collector.py  # Monthly HTML, EUR-only
└── templates/
    ├── index.html
    └── partials/_releases.html
```

## Database Schema

Two separate tables (different schemas):

- **`nso_releases`**: title, release_dt, reference_period, url
- **`ff_releases`**: title, release_dt, impact, actual, forecast, previous

Unified via `all_releases` VIEW (`UNION ALL`).

## License

MIT
