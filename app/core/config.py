"""Application configuration, loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_SNAPSHOTS_DIR = DATA_DIR / "raw_snapshots"
FIXTURES_DIR = DATA_DIR / "fixtures"


class Settings(BaseSettings):
    """Central application settings.

    All values can be overridden via environment variables or a `.env` file.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-secret-change-me"

    database_url: str = f"sqlite:///{DATA_DIR / 'sitetracker.db'}"

    # Safety: live scraping of real websites is opt-in only.
    enable_live_monitoring: bool = False
    enable_scheduler: bool = False

    user_agent: str = (
        "ChangeLensBot/0.1 "
        "(+https://github.com/yourname/site-tracker-analytics; portfolio project)"
    )
    request_timeout_seconds: float = 15.0
    request_max_retries: int = 2
    per_domain_delay_seconds: float = 3.0
    store_duplicate_snapshots: bool = False

    # Change detection: patterns considered "noise" and stripped before diffing.
    ignored_text_patterns: list[str] = [
        r"\b\d{1,2}:\d{2}(:\d{2})?\s?(am|pm)?\b",  # clock timestamps
        r"©\s?\d{4}.*",  # copyright lines
        r"all rights reserved",
        r"we use cookies.*",
        r"accept cookies.*",
        r"\bcopyright\s?\d{4}\b",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
