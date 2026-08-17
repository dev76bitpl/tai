"""Tests for scripts/dev-guards/guard_release_tag.py.

Zasada A: every guard proves (1) it blocks what it must, (2) it passes the rest.

The third case is the one this guard was rewritten for: it must also pass when it
COULD NOT CHECK. On 2026-08-17 GitHub answered 503, the old guard read that as "the
release is missing" and stopped every commit in the repository — twice, in two parallel
sessions — while the release had been published for a month.
"""
import importlib.util
import json
import subprocess
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "scripts" / "dev-guards" / "guard_release_tag.py"


def _load():
    spec = importlib.util.spec_from_file_location("guard_release_tag", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g = _load()


class _Result:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo that looks released: a CHANGELOG and a manifest pinning v1.2.3."""
    (tmp_path / "CHANGELOG.md").write_text("# changelog\n", encoding="utf-8")
    (tmp_path / ".release-please-manifest.json").write_text(json.dumps({".": "1.2.3"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _gh(result):
    """Patch subprocess.run so `gh release list` returns `result` (or raises it)."""
    def fake(cmd, *a, **kw):
        if cmd[:3] == ["gh", "release", "list"]:
            if isinstance(result, Exception):
                raise result
            return result
        return _Result(0, "abc1234 chore: release main\n")
    return mock.patch.object(g.subprocess, "run", side_effect=fake)


def test_should_pass_when_the_release_exists(repo, capsysbinary):
    with _gh(_Result(0, json.dumps([{"tagName": "v1.2.3"}, {"tagName": "v1.2.2"}]))):
        assert g.main() == 0


# The case the guard is FOR: the release genuinely is not there.
def test_should_block_when_the_release_is_confirmed_missing(repo, capsysbinary):
    with _gh(_Result(0, json.dumps([{"tagName": "v1.2.2"}]))):
        assert g.main() == 1
    out = capsysbinary.readouterr().out.decode("utf-8")
    assert "[BLOCK]" in out
    assert "gh release create v1.2.3" in out


# --- "could not check" — every one of these must PASS, not block ---

def test_should_pass_when_github_is_down(repo, capsysbinary):
    """503 from the API: non-zero exit, no usable output."""
    with _gh(_Result(1, "")):
        assert g.main() == 0
    assert "[WARN]" in capsysbinary.readouterr().out.decode("utf-8")


def test_should_pass_when_gh_prints_an_error_but_exits_zero(repo):
    """
    Observed in the wild: `gh` writes the 503 body to stdout and still exits 0. Reading
    the exit code alone would conclude "no releases" from an answer never received.
    """
    with _gh(_Result(0, '{"message": "No server is currently available"}')):
        assert g.main() == 0


def test_should_pass_when_the_output_is_not_json(repo):
    with _gh(_Result(0, "gh: command failed\n")):
        assert g.main() == 0


def test_should_pass_when_gh_is_not_installed(repo):
    with _gh(FileNotFoundError("gh")):
        assert g.main() == 0


def test_should_pass_when_gh_hangs(repo):
    with _gh(subprocess.TimeoutExpired(cmd="gh", timeout=15)):
        assert g.main() == 0


# --- repositories the guard has no business in ---

def test_should_ignore_a_repo_without_a_changelog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert g.main() == 0


def test_should_ignore_a_repo_without_a_manifest_version(tmp_path, monkeypatch):
    (tmp_path / "CHANGELOG.md").write_text("# changelog\n", encoding="utf-8")
    (tmp_path / ".release-please-manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert g.main() == 0
