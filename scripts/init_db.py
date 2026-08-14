"""Database initialization: create tables and seed nso_sources."""
import asyncio
import logging
from pathlib import Path

import asyncpg
from sqlalchemy import text

from app.database import engine
from app.config import settings


SEED_SOURCES = [
    ("eurostat", "Eurostat", "EU", "ics"),
    ("istat", "Istat", "IT", "ics"),
    ("ine", "INE", "ES", "ics"),
    ("destatis", "Destatis", "DE", "html"),
    ("insee", "INSEE", "FR", "html"),
    ("cso", "CSO", "IE", "api"),
]


def _parse_db_url(url: str) -> dict:
    """Extract connection params from SQLAlchemy URL for asyncpg."""
    # postgresql+asyncpg://user:pass@host:port/dbname
    import re
    m = re.match(r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", url)
    if not m:
        return {}
    return {
        "user": m.group(1),
        "password": m.group(2),
        "host": m.group(3),
        "port": int(m.group(4)),
        "database": m.group(5),
    }


async def init_db():
    """Create tables from schema.sql, then seed nso_sources."""
    logging.info("Creating tables from schema.sql...")

    schema_path = Path(__file__).parent.parent / "sql" / "schema.sql"
    schema_sql = schema_path.read_text()

    # Use asyncpg directly to execute the full multi-statement schema
    params = _parse_db_url(settings.database_url)
    conn = await asyncpg.connect(**params)
    try:
        await conn.execute(schema_sql)
    finally:
        await conn.close()

    logging.info("Seeding nso_sources...")
    async with engine.begin() as conn:
        for code, name, country, feed_type in SEED_SOURCES:
            await conn.execute(
                text("""
                    INSERT INTO nso_sources (code, name, country, feed_type, is_active)
                    VALUES (:code, :name, :country, :feed_type, TRUE)
                    ON CONFLICT (code) DO UPDATE SET
                        name = EXCLUDED.name,
                        country = EXCLUDED.country,
                        feed_type = EXCLUDED.feed_type
                """),
                {"code": code, "name": name, "country": country, "feed_type": feed_type},
            )

    logging.info("Database initialized successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())
