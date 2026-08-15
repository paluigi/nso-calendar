"""Run each NSO collector standalone and print a summary.

Usage (from repo root):
    .venv/bin/python local_tests/test_collectors.py
    .venv/bin/python local_tests/test_collectors.py istat destatis
"""
from __future__ import annotations

import sys
import traceback

from app.collectors.ics_collector import EurostatCollector, IstatCollector, INECollector
from app.collectors.destatis_collector import DestatisCollector
from app.collectors.insee_collector import INSEECollector
from app.collectors.cso_collector import CSOCollector

COLLECTORS = {
    "eurostat": EurostatCollector,
    "istat": IstatCollector,
    "ine": INECollector,
    "destatis": DestatisCollector,
    "insee": INSEECollector,
    "cso": CSOCollector,
}


def main(argv: list[str]) -> int:
    names = argv[1:] or list(COLLECTORS)
    failures = 0

    for name in names:
        cls = COLLECTORS[name]
        print(f"\n{'=' * 60}\n{name} ({cls.__name__})\n{'=' * 60}")
        try:
            records = cls().collect()
            print(f"-> {len(records)} records")
            for r in records[:5]:
                print(f"   {r.release_dt:%Y-%m-%d %H:%M} | {r.title[:70]}"
                      f"{f' | ref={r.reference_period}' if r.reference_period else ''}")
            if len(records) > 5:
                print(f"   ... and {len(records) - 5} more")
            if not records:
                failures += 1
        except Exception:
            failures += 1
            traceback.print_exc()

    print(f"\nSummary: {len(names) - failures}/{len(names)} collectors returned data")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
