"""Validation and normalisation of records returned by the Elexon datasets.

External payloads are treated as untrusted.  Invalid records are skipped and
counted rather than crashing an analysis, and every internal timestamp is UTC.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from datetime import datetime

from app.models.domain import ActualRecord, ForecastRecord, NormalizationStats
from app.services.timeutils import parse_iso_datetime


def parse_generation_mw(value: object) -> float | None:
    """Convert a generation value to a finite, non-negative MW number."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and value.strip():
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_forecast_records(raw_records: Iterable[object]) -> tuple[list[ForecastRecord], NormalizationStats]:
    """Validate, de-duplicate and sort WINDFOR records.

    Exact duplicates (same delivery time, publication time and value) are
    collapsed.  Different forecast versions are intentionally retained so the
    decision-time selector can choose between them.
    """
    stats = NormalizationStats()
    records: list[ForecastRecord] = []
    seen: set[tuple[datetime, datetime, float]] = set()

    for index, raw in enumerate(raw_records):
        stats.received += 1
        if not isinstance(raw, Mapping):
            stats.skipped_malformed += 1
            continue

        dataset = _optional_text(raw.get("dataset"))
        if dataset is not None and dataset.upper() != "WINDFOR":
            stats.skipped_wrong_dataset += 1
            continue

        try:
            start_time = parse_iso_datetime(raw.get("startTime"))
            publish_time = parse_iso_datetime(raw.get("publishTime"))
        except ValueError:
            stats.skipped_invalid_timestamp += 1
            continue

        # WINDFOR is an hourly dataset.  Non-hour-aligned records are rejected
        # rather than guessed at, because shifting them would break matching.
        if start_time.minute != 0 or start_time.second != 0 or start_time.microsecond != 0:
            stats.skipped_unaligned += 1
            continue

        generation = parse_generation_mw(raw.get("generation"))
        if generation is None:
            stats.skipped_invalid_generation += 1
            continue

        key = (start_time, publish_time, generation)
        if key in seen:
            stats.duplicate_exact += 1
            continue
        seen.add(key)

        records.append(
            ForecastRecord(
                start_time=start_time,
                publish_time=publish_time,
                generation_mw=generation,
                source_index=index,
            )
        )

    records.sort(key=lambda r: (r.start_time, r.publish_time, r.generation_mw, r.source_index))
    stats.valid = len(records)
    if stats.skipped_unaligned:
        stats.warnings.append(
            f"{stats.skipped_unaligned} WINDFOR record(s) were not aligned to the hour and were skipped."
        )
    return records, stats


def normalize_actual_records(raw_records: Iterable[object]) -> tuple[list[ActualRecord], NormalizationStats]:
    """Filter FUELHH records to WIND, validate them and resolve revisions.

    When more than one WIND record exists for a delivery interval, the latest
    ``publishTime`` wins.  If two records share that publication time, the
    higher generation value wins and the ambiguity is counted.
    """
    stats = NormalizationStats()
    candidates: list[ActualRecord] = []
    exact_seen: set[tuple[datetime, datetime, float]] = set()

    for index, raw in enumerate(raw_records):
        stats.received += 1
        if not isinstance(raw, Mapping):
            stats.skipped_malformed += 1
            continue

        dataset = _optional_text(raw.get("dataset"))
        if dataset is not None and dataset.upper() != "FUELHH":
            stats.skipped_wrong_dataset += 1
            continue

        fuel_type = _optional_text(raw.get("fuelType"))
        if fuel_type is None or fuel_type.upper() != "WIND":
            stats.skipped_non_wind += 1
            continue

        try:
            start_time = parse_iso_datetime(raw.get("startTime"))
            publish_time = parse_iso_datetime(raw.get("publishTime"))
        except ValueError:
            stats.skipped_invalid_timestamp += 1
            continue

        generation = parse_generation_mw(raw.get("generation"))
        if generation is None:
            stats.skipped_invalid_generation += 1
            continue

        key = (start_time, publish_time, generation)
        if key in exact_seen:
            stats.duplicate_exact += 1
            continue
        exact_seen.add(key)

        candidates.append(
            ActualRecord(
                start_time=start_time,
                publish_time=publish_time,
                generation_mw=generation,
                settlement_date=_optional_text(raw.get("settlementDate")),
                settlement_period=_optional_int(raw.get("settlementPeriod")),
                source_index=index,
            )
        )

    candidates.sort(key=lambda r: (r.start_time, r.publish_time, r.generation_mw, r.source_index))
    by_start: dict[datetime, ActualRecord] = {}
    ambiguous_starts: set[datetime] = set()
    for record in candidates:
        existing = by_start.get(record.start_time)
        if existing is not None:
            stats.duplicate_superseded += 1
            if record.publish_time == existing.publish_time and record.generation_mw != existing.generation_mw:
                ambiguous_starts.add(record.start_time)
            elif record.publish_time <= existing.publish_time:
                # Keep the first deterministic winner if a later sort entry is
                # older; this should not occur with the sort above.
                continue
        by_start[record.start_time] = record

    stats.ambiguous_duplicates = len(ambiguous_starts)
    records = sorted(by_start.values(), key=lambda r: r.start_time)
    stats.valid = len(records)
    if stats.duplicate_superseded:
        stats.warnings.append(
            f"{stats.duplicate_superseded} superseded FUELHH record(s) were replaced by the latest publication."
        )
    return records, stats
