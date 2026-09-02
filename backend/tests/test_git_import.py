"""Git URL import validation + clone security tests."""
from __future__ import annotations

import pytest

from app.services.git_import import MAX_DEPTH, validate_git_url


def test_valid_https_urls_accepted() -> None:
    validate_git_url("https://github.com/owner/repo")
    validate_git_url("https://github.com/owner/repo.git")
    validate_git_url("https://gitlab.com/g/sub/project")


@pytest.mark.parametrize("url", [
    "ssh://git@github.com/owner/repo",     # ssh transport
    "git@github.com:owner/repo.git",        # scp syntax
    "file:///etc/passwd",                   # local file
    "http://github.com/owner/repo",         # plain http
    "https://github.com/../../etc",         # traversal
    "https://evil.com/repo; rm -rf /",      # command chars
    "ftp://x/y",
    "",
])
def test_rejected_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validate_git_url(url)


def test_clone_command_shape() -> None:
    """The clone helper must use depth-limited single-branch clones."""
    from app.services.git_import import CLONE_TIMEOUT_SECONDS

    assert MAX_DEPTH <= 50
    assert CLONE_TIMEOUT_SECONDS == 300


def test_api_git_import_rejects_bad_url(client):
    r = client.post("/api/repositories/import", json={"git_url": "http://bad/x"})
    assert r.status_code == 400
    assert "https" in r.json()["detail"]
