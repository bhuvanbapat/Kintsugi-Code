"""Application configuration via environment variables with .env support."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        env_prefix="CODEFORGE_",
        extra="ignore",
    )

    app_name: str = "CodeForge"
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{Path(__file__).resolve().parents[2] / 'codeforge.db'}"
    )
    sqlite_path: str = Field(
        default_factory=lambda: str(Path(__file__).resolve().parents[2] / "codeforge.db")
    )

    llm_provider: Literal["openai", "mock"] = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 60.0

    max_index_file_size_bytes: int = 2 * 1024 * 1024
    max_repository_files: int = 20000
    scan_timeout_seconds: float = 300.0

    agent_max_iterations: int = 12
    tool_timeout_seconds: float = 60.0
    command_timeout_seconds: float = 300.0
    max_tool_output_bytes: int = 200_000

    context_budget_tokens: int = 8000
    retrieval_max_candidates: int = 50

    eval_on: bool = True


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
