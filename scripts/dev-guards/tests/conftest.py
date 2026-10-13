import os

import pytest

from harness import make_repo


@pytest.fixture
def repo(tmp_path):
    """An empty git repository on `main` with the guards copied in."""
    return make_repo(tmp_path / "repo")


@pytest.fixture(autouse=True)
def _no_git_environment_from_a_hook(monkeypatch):
    """Drop every GIT_* variable before each test.

    The suite runs from a pre-commit hook, where git exports GIT_INDEX_FILE and — in a linked
    worktree — GIT_DIR. Any `git` a test starts would then act on the REAL repository instead of
    its temp one: `git init` flips core.bare, `git add` stages fixtures into the real index.
    Cleaning per call (harness.clean_env) depends on every test remembering it; this does not.
    """
    for name in [key for key in os.environ if key.startswith("GIT_")]:
        monkeypatch.delenv(name)
