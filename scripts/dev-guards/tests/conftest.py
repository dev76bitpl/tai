import pytest

from harness import make_repo


@pytest.fixture
def repo(tmp_path):
    """An empty git repository on `main` with the guards copied in."""
    return make_repo(tmp_path / "repo")
