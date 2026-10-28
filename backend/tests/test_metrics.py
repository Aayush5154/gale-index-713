from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.models.domain import ForecastRecord, ForecastSelection, HourlyActual
from app.services.comparison import build_comparison
from app.services.metrics import (
    compute_accuracy,
    compute_coverage,
    compute_daily,
    compute_error_histogram,
)

LDN = ZoneInfo("Europe/London")
HOUR = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_row(hour, forecast, actual, *, cutoff=None, mape_min=1.0):
    selected = (
        ForecastRecord(start_time=hour, publish_time=hour - timedelta(hours=12), generation_mw=forecast)
        if forecast is not None
        else None
    )
    selection = ForecastSelection(
        delivery_start=hour,
        cutoff=cutoff or hour - timedelta(hours=12),
        selected=selected,
        eligible_count=1 if selected else 0,
        previous=None,
        duplicate_publication=False,
        stale=False,
    )
    hourly_actual = HourlyActual(
        start_time=hour,
        generation_mw=actual,
        half_hour_values=(actual, actual) if actual is not None else (),
    )
    rows = build_comparison(
        hours=[hour],
        cutoffs={hour: selection.cutoff},
        selections={hour: selection},
        hourly_actuals={hour: hourly_actual},
        mape_min_actual_mw=mape_min,
    )
    return rows[0]


def test_known_metrics():
    rows = [
        make_row(HOUR, 10, 8),
        make_row(HOUR + timedelta(hours=1), 20, 22),
        make_row(HOUR + timedelta(hours=2), 30, 25),
    ]
    metrics = compute_accuracy(rows)
    assert metrics.mae_mw == pytest.approx(3.0)
    assert metrics.rmse_mw == pytest.approx(11**0.5, abs=1e-3)
    assert metrics.mbe_mw == pytest.approx(5 / 3, abs=1e-3)
    assert metrics.mape_percent == pytest.approx((25.0 + 2 / 22 * 100 + 20.0) / 3, abs=1e-3)
    assert metrics.mape_valid_count == 3
    assert metrics.mape_excluded_count == 0
    assert metrics.max_abs_error_mw == 5


def test_bias_sign_convention():
    over = compute_accuracy([make_row(HOUR, 12, 10)])
    under = compute_accuracy([make_row(HOUR, 8, 10)])
    assert over.mbe_mw == 2
    assert under.mbe_mw == -2


def test_zero_actual_is_excluded_from_mape_but_kept_in_mae():
    rows = [make_row(HOUR, 5, 0), make_row(HOUR + timedelta(hours=1), 12, 10)]
    metrics = compute_accuracy(rows)
    assert metrics.mae_mw == 3.5
    assert metrics.mbe_mw == 3.5
    assert metrics.mape_valid_count == 1
    assert metrics.mape_excluded_count == 1
    assert metrics.mape_percent == 20.0


def test_near_zero_actual_below_threshold_is_excluded_from_mape():
    rows = [make_row(HOUR, 5, 0.5)]
    metrics = compute_accuracy(rows)
    assert metrics.mape_percent is None
    assert metrics.mape_excluded_count == 1
    assert metrics.mae_mw == 4.5


def test_empty_dataset_returns_empty_metrics():
    metrics = compute_accuracy([])
    assert metrics.mae_mw is None
    assert metrics.rmse_mw is None
    assert metrics.mbe_mw is None
    assert metrics.mape_percent is None
    assert metrics.max_abs_error_mw is None


def test_coverage_separates_missing_forecast_and_missing_actual():
    rows = [
        make_row(HOUR, 10, 10),
        make_row(HOUR + timedelta(hours=1), None, 10),
        make_row(HOUR + timedelta(hours=2), 10, None),
        make_row(HOUR + timedelta(hours=3), None, None),
    ]
    coverage = compute_coverage(rows)
    assert coverage.expected_intervals == 4
    assert coverage.valid_pairs == 1
    assert coverage.forecast_available == 2
    assert coverage.missing_forecast == 2
    assert coverage.missing_actual == 2
    assert coverage.missing_both == 1
    assert coverage.coverage_percent == 50.0
    assert coverage.valid_pair_percent == 25.0


def test_missing_pairs_do_not_enter_metrics():
    rows = [
        make_row(HOUR, 10, 10),
        make_row(HOUR + timedelta(hours=1), 99, None),
        make_row(HOUR + timedelta(hours=2), None, 99),
    ]
    metrics = compute_accuracy(rows)
    assert metrics.mae_mw == 0
    assert metrics.max_abs_error_mw == 0
    assert metrics.mape_valid_count == 1


def test_daily_metrics_group_by_london_delivery_date():
    rows = [
        make_row(HOUR, 12, 10),
        make_row(HOUR + timedelta(hours=23), 14, 10),
        make_row(HOUR + timedelta(hours=24), 16, 10),
    ]
    daily = compute_daily(rows, LDN)
    assert len(daily) == 2
    assert daily[0].day.isoformat() == "2026-01-01"
    assert daily[0].valid_pairs == 2
    assert daily[0].mae_mw == 3
    assert daily[1].day.isoformat() == "2026-01-02"
    assert daily[1].mae_mw == 6


def test_histogram_includes_zero_and_all_pairs():
    rows = [
        make_row(HOUR, 12, 10),
        make_row(HOUR + timedelta(hours=1), 8, 10),
        make_row(HOUR + timedelta(hours=2), 10, 10),
    ]
    histogram = compute_error_histogram(rows)
    assert histogram.total_pairs == 3
    assert sum(bin.count for bin in histogram.bins) == 3
    assert any(bin.lower_mw <= 0 <= bin.upper_mw for bin in histogram.bins)
    assert histogram.bin_width_mw > 0
