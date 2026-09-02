"""Shared fixtures: temp repo, store, and FastAPI client."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLE_REPO = BACKEND_DIR.parent / "examples" / "sample_repo"


@pytest.fixture()
def temp_store(tmp_path: Path):
    from app.services.store import Store

    store = Store(db_path=str(tmp_path / "test.db"))
    yield store
    store.close()


@pytest.fixture()
def sample_repo_copy(tmp_path: Path) -> Path:
    """Copy of the sample repo so tests can index/patch without touching the original."""
    dest = tmp_path / "sample_repo"
    shutil.copytree(SAMPLE_REPO, dest)
    return dest


@pytest.fixture()
def indexed_repo(temp_store, sample_repo_copy, monkeypatch):
    from app.models.domain import Repository
    from app.services import rag_service
    from app.services.indexer import index_repository

    # Point every module that resolves the store at our temp store.
    monkeypatch.setattr(rag_service, "get_store", lambda: temp_store)
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "get_store", lambda: temp_store)

    repo = Repository(name=sample_repo_copy.name, root_path=str(sample_repo_copy))
    temp_store.upsert_repository(repo)
    index_repository(repo, temp_store)
    rag_service.invalidate_retriever(repo.id)
    yield repo
    rag_service.invalidate_retriever(repo.id)


@pytest.fixture()
def client(temp_store, monkeypatch):
    from app.main import app
    from app.services import rag_service

    monkeypatch.setattr(rag_service, "get_store", lambda: temp_store)
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "get_store", lambda: temp_store)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
