"""Application configuration loaded from environment variables.

All settings are intentionally plain and bounded.  The only required external
configuration is the Elexon API base URL, which already has a safe public
default.  Secrets are not used by this application.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Wind Forecast Analytics API"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Data source
    data_mode: Literal["live", "fixture"] = "live"
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = Field(default=45.0, gt=0, le=120)
    elexon_connect_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    elexon_max_retries: int = Field(default=2, ge=0, le=5)
    elexon_concurrency: int = Field(default=4, ge=1, le=10)
    elexon_chunk_days: int = Field(default=6, ge=1, le=7)
    elexon_forecast_lookback_days: int = Field(default=3, ge=1, le=14)
    elexon_user_agent: str = "wind-forecast-analytics/1.0 (portfolio analytics)"

    # Cache
    cache_ttl_seconds: int = Field(default=900, ge=30, le=86_400)
    cache_max_entries: int = Field(default=128, ge=8, le=2_048)
    prewarm_default_range: bool = True

    # Market / analysis defaults
    market_timezone: str = "Europe/London"
    default_from_date: str = "2026-01-01"
    default_to_date: str = "2026-01-31"
    default_cutoff_time: str = "09:20"
    max_range_days: int = Field(default=92, ge=1, le=366)
    mape_min_actual_mw: float = Field(default=1.0, ge=0)
    stale_forecast_hours: float = Field(default=48.0, gt=0)

    # HTTP
    frontend_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    # Fixture mode
    fixture_dir: Path = Path(__file__).resolve().parents[2] / "fixtures"

    @field_validator("elexon_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("default_cutoff_time")
    @classmethod
    def _validate_cutoff_time(cls, value: str) -> str:
        from datetime import time

        time.fromisoformat(value)
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def is_fixture_mode(self) -> bool:
        return self.data_mode == "fixture"


@lru_cache
def get_settings() -> Settings:
    return Settings()
