"""Decision-time forecast selection.

Eligibility is deliberately strict:

* the forecast must target the exact delivery hour;
* its publication timestamp must be at or before the decision cut-off;
* a forecast published at or after the delivery timestamp is never eligible.

Among eligible versions the latest publication wins.  Ties are resolved by the
higher generation value (a documented deterministic rule, not a market view).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app.models.domain import ForecastRecord, ForecastSelection


def index_forecasts_by_delivery(
    records: list[ForecastRecord],
) -> dict[datetime, list[ForecastRecord]]:
    index: dict[datetime, list[ForecastRecord]] = defaultdict(list)
    for record in records:
        index[record.start_time].append(record)
    for versions in index.values():
        versions.sort(key=lambda r: (r.publish_time, r.generation_mw, r.source_index))
    return dict(index)


def select_decision_time_forecasts(
    *,
    hours: list[datetime],
    cutoffs: dict[datetime, datetime],
    records: list[ForecastRecord],
    stale_after_hours: float = 48.0,
) -> dict[datetime, ForecastSelection]:
    index = index_forecasts_by_delivery(records)
    selections: dict[datetime, ForecastSelection] = {}

    for hour in hours:
        cutoff = cutoffs[hour]
        eligible = [
            record
            for record in index.get(hour, [])
            if record.publish_time <= cutoff and record.publish_time < hour
        ]
        eligible.sort(key=lambda r: (r.publish_time, r.generation_mw, r.source_index))

        selected = eligible[-1] if eligible else None
        previous = None
        duplicate_publication = False
        stale = False

        if selected is not None:
            earlier = [r for r in eligible if r.publish_time < selected.publish_time]
            previous = earlier[-1] if earlier else None
            duplicate_publication = (
                sum(1 for r in eligible if r.publish_time == selected.publish_time) > 1
            )
            lead_hours = (hour - selected.publish_time).total_seconds() / 3600
            stale = lead_hours > stale_after_hours

        selections[hour] = ForecastSelection(
            delivery_start=hour,
            cutoff=cutoff,
            selected=selected,
            eligible_count=len(eligible),
            previous=previous,
            duplicate_publication=duplicate_publication,
            stale=stale,
        )

    return selections


def summarise_publication_usage(selections: dict[datetime, ForecastSelection]) -> dict[str, object]:
    selected = [s.selected for s in selections.values() if s.selected is not None]
    publications = sorted({r.publish_time for r in selected if r is not None})
    leads = [
        (s.delivery_start - s.selected.publish_time).total_seconds() / 3600
        for s in selections.values()
        if s.selected is not None
    ]
    return {
        "available": len(selected),
        "missing": len(selections) - len(selected),
        "distinct_publications": len(publications),
        "publication_min": publications[0] if publications else None,
        "publication_max": publications[-1] if publications else None,
        "lead_time_min_hours": min(leads) if leads else None,
        "lead_time_max_hours": max(leads) if leads else None,
        "duplicate_publication_intervals": sum(
            1 for s in selections.values() if s.duplicate_publication
        ),
        "stale_intervals": sum(1 for s in selections.values() if s.stale),
    }
