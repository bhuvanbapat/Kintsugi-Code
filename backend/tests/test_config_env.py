"""Configuration contract tests: env-file location and precedence."""
from __future__ import annotations

import pathlib

from app.core.config import Settings


def test_env_file_resolves_to_backend_dotenv() -> None:
    """The documented contract: settings load from backend/.env —
    not backend/app/.env (a past off-by-one in the parents index)."""
    backend = pathlib.Path(__file__).resolve().parents[1]
    model_config = Settings.model_config
    env_file = str(model_config.get("env_file", ""))
    expected = str(backend / ".env")
    assert pathlib.Path(env_file).resolve() == pathlib.Path(expected).resolve(), (
        f"env_file must point at backend/.env, got {env_file}"
    )


def test_env_file_is_actually_loaded(tmp_path, monkeypatch) -> None:
    """End-to-end: a real backend/.env file provides values (and a stray
    backend/app/.env does not win)."""
    backend = pathlib.Path(__file__).resolve().parents[1]
    env_file = backend / ".env"
    stray = backend / "app" / ".env"
    created = []
    try:
        env_file.write_text("CODEFORGE_LOG_LEVEL=FROM_BACKEND_ENV\n", encoding="utf-8")
        created.append(env_file)
        if not stray.exists():
            stray.parent.mkdir(parents=True, exist_ok=True)
            stray.write_text("CODEFORGE_LOG_LEVEL=FROM_APP_STRAY\n", encoding="utf-8")
            created.append(stray)
        monkeypatch.delenv("CODEFORGE_LOG_LEVEL", raising=False)
        s = Settings()
        assert s.log_level == "FROM_BACKEND_ENV", (
            f"backend/.env not loaded or overridden: got {s.log_level}"
        )
    finally:
        for p in created:
            p.unlink(missing_ok=True)


def test_env_vars_take_precedence_over_env_file(tmp_path, monkeypatch) -> None:
    """Real environment variables outrank .env values (pydantic-settings
    default precedence) — the documented behavior for deployment overrides."""
    backend = pathlib.Path(__file__).resolve().parents[1]
    env_file = backend / ".env"
    wrote = False
    try:
        if not env_file.exists():
            env_file.write_text("CODEFORGE_LOG_LEVEL=FROM_FILE\n", encoding="utf-8")
            wrote = True
        monkeypatch.setenv("CODEFORGE_LOG_LEVEL", "FROM_PROCESS_ENV")
        s = Settings()
        assert s.log_level == "FROM_PROCESS_ENV"
    finally:
        if wrote:
            env_file.unlink(missing_ok=True)
