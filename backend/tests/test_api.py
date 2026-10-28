from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fakes import StaticSource, two_day_records


def make_app(*, fail: bool = False):
    settings = Settings(
        environment="test",
        data_mode="fixture",
        prewarm_default_range=False,
        default_from_date="2026-01-01",
        default_to_date="2026-01-02",
        log_level="WARNING",
    )
    actuals, forecasts = two_day_records()
    source = StaticSource(actuals, forecasts, fail=fail)
    return create_app(settings, source=source), source


@pytest.fixture
def client():
    app, source = make_app()
    with TestClient(app) as test_client:
        yield test_client, source


def test_health_reports_dependency_and_data_mode(client):
    test_client, _ = client
    response = test_client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "fixture"
    assert payload["is_synthetic"] is True
    assert payload["dependencies"][0]["name"] == "Test source"


def test_metadata_contains_sources_and_methodology(client):
    test_client, _ = client
    response = test_client.get("/api/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert {dataset["key"] for dataset in payload["datasets"]} == {"FUELHH", "WINDFOR"}
    assert payload["target_period"] == {"from_date": "2026-01-01", "to_date": "2026-01-02"}
    assert payload["timezone"] == "Europe/London"
    assert payload["is_synthetic"] is True
    assert len(payload["metric_definitions"]) >= 5
    assert payload["resolution"]["forecast"] == "hourly"


def test_metrics_endpoint_contract(client):
    test_client, _ = client
    response = test_client.get("/api/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["expected_intervals"] == 48
    assert payload["coverage"]["expected_intervals"] == 48
    assert payload["coverage"]["valid_pairs"] == 48
    assert payload["coverage"]["coverage_percent"] == 100.0
    assert payload["metrics"]["mae_mw"] == pytest.approx(750.0)
    assert payload["metrics"]["mbe_mw"] == pytest.approx(750.0)
    assert payload["metrics"]["rmse_mw"] == pytest.approx(625000**0.5, rel=1e-5)
    assert payload["decision_context"]["distinct_publications"] == 2
    assert payload["data_source"]["data_mode"] == "fixture"
    assert payload["histogram"]["total_pairs"] == 48


def test_comparison_endpoint_does_not_leak_post_cutoff_forecast(client):
    test_client, _ = client
    response = test_client.get("/api/comparison")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["intervals"]) == 48
    assert len(payload["half_hourly_actuals"]) == 96
    assert payload["intervals"][0]["status"] == "matched"
    assert payload["intervals"][0]["forecast_mw"] == 10500
    assert payload["intervals"][0]["actual_mw"] == 10000
    assert payload["intervals"][-1]["forecast_mw"] == 11000
    assert all(interval["forecast_mw"] != 99999 for interval in payload["intervals"])


def test_forecasts_endpoint_exposes_publication_and_cutoff(client):
    test_client, _ = client
    response = test_client.get("/api/forecasts", params={"from_date": "2026-01-02", "to_date": "2026-01-02"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["expected_intervals"] == 24
    assert payload["summary"]["available"] == 24
    first = payload["intervals"][0]
    assert first["forecast_publication_utc"] == "2026-01-01T07:30:00Z"
    assert first["cutoff_utc"] == "2026-01-01T09:20:00Z"
    assert first["lead_time_hours"] == 16.5
    assert first["eligible_forecast_count"] >= 1


def test_daily_endpoint_returns_each_day(client):
    test_client, _ = client
    response = test_client.get("/api/accuracy/daily")
    assert response.status_code == 200
    payload = response.json()
    assert [row["date"] for row in payload["daily"]] == ["2026-01-01", "2026-01-02"]
    assert payload["daily"][0]["mae_mw"] == pytest.approx(500.0)
    assert payload["daily"][1]["mae_mw"] == pytest.approx(1000.0)
    assert all(row["valid_pairs"] == 24 for row in payload["daily"])


def test_invalid_date_range_uses_consistent_error_shape(client):
    test_client, _ = client
    response = test_client.get("/api/metrics", params={"from_date": "2026-01-05", "to_date": "2026-01-01"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "invalid_query"
    assert payload["error"]["request_id"]


def test_malformed_date_is_a_422(client):
    test_client, _ = client
    response = test_client.get("/api/metrics", params={"from_date": "not-a-date"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_query"
    assert "errors" in response.json()["error"]["details"]


def test_fixed_mode_requires_cutoff(client):
    test_client, _ = client
    response = test_client.get("/api/metrics", params={"cutoff_mode": "fixed"})
    assert response.status_code == 422
    assert "cutoff_datetime" in response.json()["error"]["message"]


def test_fixed_cutoff_after_delivery_is_rejected(client):
    test_client, _ = client
    response = test_client.get(
        "/api/metrics",
        params={"from_date": "2026-01-02", "to_date": "2026-01-02", "cutoff_mode": "fixed", "cutoff_datetime": "2026-01-02T00:00"},
    )
    assert response.status_code == 422
    assert "before the first delivery interval" in response.json()["error"]["message"]


def test_future_period_is_rejected(client):
    test_client, _ = client
    response = test_client.get("/api/metrics", params={"from_date": "2035-01-01", "to_date": "2035-01-02"})
    assert response.status_code == 422
    assert "cannot extend beyond today" in response.json()["error"]["message"]


def test_request_id_header_is_returned(client):
    test_client, _ = client
    response = test_client.get("/api/health", headers={"X-Request-ID": "test-request-123"})
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_cors_preflight_for_frontend_origin(client):
    test_client, _ = client
    response = test_client.options(
        "/api/metrics",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_upstream_failure_returns_503_without_stack_trace():
    app, _ = make_app(fail=True)
    with TestClient(app) as test_client:
        response = test_client.get("/api/metrics")
    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "upstream_unavailable"
    assert payload["error"]["message"]
    assert "Traceback" not in response.text
    assert "site-packages" not in response.text


def test_unknown_route_is_json_404(client):
    test_client, _ = client
    response = test_client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_openapi_schema_is_available(client):
    test_client, _ = client
    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert "/api/comparison" in payload["paths"]
    assert "/api/metrics" in payload["paths"]
