"""Forecast/actual matching at exact hourly delivery timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.models.domain import ForecastSelection, HourlyActual

ComparisonStatus = Literal["matched", "missing_forecast", "missing_actual", "missing_both"]


@dataclass(frozen=True, slots=True)
class ComparisonRow:
    delivery_start: datetime
    cutoff: datetime
    selection: ForecastSelection
    actual: HourlyActual
    status: ComparisonStatus
    signed_error_mw: float | None
    absolute_error_mw: float | None
    squared_error_mw2: float | None
    absolute_percentage_error: float | None

    @property
    def forecast_mw(self) -> float | None:
        return self.selection.selected.generation_mw if self.selection.selected else None

    @property
    def actual_mw(self) -> float | None:
        return self.actual.generation_mw

    @property
    def is_valid_pair(self) -> bool:
        return self.status == "matched"


def build_comparison(
    *,
    hours: list[datetime],
    cutoffs: dict[datetime, datetime],
    selections: dict[datetime, ForecastSelection],
    hourly_actuals: dict[datetime, HourlyActual],
    mape_min_actual_mw: float,
) -> list[ComparisonRow]:
    rows: list[ComparisonRow] = []

    for hour in hours:
        selection = selections[hour]
        actual = hourly_actuals[hour]
        forecast = selection.selected.generation_mw if selection.selected else None
        actual_value = actual.generation_mw

        if forecast is not None and actual_value is not None:
            status: ComparisonStatus = "matched"
            signed = forecast - actual_value
            absolute = abs(signed)
            squared = signed * signed
            pct = (absolute / actual_value * 100.0) if actual_value >= mape_min_actual_mw > 0 else None
        else:
            status = (
                "missing_both"
                if forecast is None and actual_value is None
                else "missing_forecast"
                if forecast is None
                else "missing_actual"
            )
            signed = absolute = squared = pct = None

        rows.append(
            ComparisonRow(
                delivery_start=hour,
                cutoff=cutoffs[hour],
                selection=selection,
                actual=actual,
                status=status,
                signed_error_mw=signed,
                absolute_error_mw=absolute,
                squared_error_mw2=squared,
                absolute_percentage_error=pct,
            )
        )

    return rows
