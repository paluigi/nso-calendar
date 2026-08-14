"""Collectors package."""
from app.collectors.base import BaseNSOCollector
from app.collectors.ics_collector import EurostatCollector, IstatCollector, INECollector
from app.collectors.destatis_collector import DestatisCollector
from app.collectors.insee_collector import INSEECollector
from app.collectors.cso_collector import CSOCollector
from app.collectors.forexfactory_collector import ForexFactoryCollector

__all__ = [
    "BaseNSOCollector",
    "EurostatCollector",
    "IstatCollector",
    "INECollector",
    "DestatisCollector",
    "INSEECollector",
    "CSOCollector",
    "ForexFactoryCollector",
]
