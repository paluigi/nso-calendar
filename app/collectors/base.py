"""Base collector interface + record dataclasses re-exported for convenience."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import NSOReleaseRecord, FFReleaseRecord


class BaseNSOCollector(ABC):
    """Base class for NSO data collectors."""

    @abstractmethod
    def source_code(self) -> str:
        ...

    @abstractmethod
    def collect(self) -> list[NSOReleaseRecord]:
        ...
