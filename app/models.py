"""SQLAlchemy ORM models + collector record dataclasses."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import String, Text, ForeignKey, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.database import Base


# ============================================================
# ORM Models
# ============================================================

class NSOSource(Base):
    __tablename__ = "nso_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(Text)
    country: Mapped[str] = mapped_column(Text)
    feed_type: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    releases: Mapped[list["NSORelease"]] = relationship(back_populates="source")


class NSORelease(Base):
    __tablename__ = "nso_releases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[int] = mapped_column(ForeignKey("nso_sources.id"))
    title: Mapped[str] = mapped_column(Text)
    release_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_period: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_uid: Mapped[str] = mapped_column(Text, unique=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    source: Mapped["NSOSource"] = relationship(back_populates="releases")


class FFRelease(Base):
    __tablename__ = "ff_releases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(Text)
    release_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    release_dt_orig: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(Text, default="EUR")
    actual: Mapped[str | None] = mapped_column(Text, nullable=True)
    forecast: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_uid: Mapped[str] = mapped_column(Text, unique=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# Collector Record Dataclasses (intermediate representation)
# ============================================================

def make_uid(*parts: str) -> str:
    """Stable hash for deduplication."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


@dataclass
class NSOReleaseRecord:
    """Intermediate representation from NSO collectors."""
    source_code: str
    title: str
    release_dt: datetime          # UTC
    reference_period: str | None = None
    url: str | None = None

    @property
    def source_uid(self) -> str:
        return make_uid(self.source_code, self.title, self.release_dt.isoformat())


@dataclass
class FFReleaseRecord:
    """Intermediate representation from ForexFactory collector."""
    title: str
    release_dt: datetime          # UTC
    impact: str                   # 'high' | 'medium' | 'low'
    actual: str | None = None
    forecast: str | None = None
    previous: str | None = None
    release_dt_orig: str | None = None
    currency: str = "EUR"

    @property
    def source_uid(self) -> str:
        return make_uid("forexfactory", self.title, self.release_dt.isoformat())
