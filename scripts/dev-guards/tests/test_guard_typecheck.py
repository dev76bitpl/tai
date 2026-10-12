"""Tests for scripts/dev-guards/guard_typecheck.py — `tsc --noEmit` gates commits with TS/JS
files in a node project. A fake `tsc` stands in for the compiler."""
import os
import stat

import pytest

from harness import BLOCKED, run_guard, stage

GUARD = "guard_typecheck"

posix_only = pytest.mark.skipif(os.name == "nt", reason="the fake tsc is a shell script")


def _fake_tsc(repo, exit_code):
    tsc = repo / "node_modules" / ".bin" / "tsc"
    tsc.parent.mkdir(parents=True, exist_ok=True)
    tsc.write_text(
        "#!/bin/sh\n"
        '[ "$1" = "--version" ] && exit 0\n'
        f'[ {exit_code} -ne 0 ] && echo "src/a.ts(1,7): error TS2322: Type mismatch"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    tsc.chmod(tsc.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def node_repo(repo):
    stage(repo, "package.json", "{}\n")
    return repo


@posix_only
def test_should_block_and_show_errors_when_tsc_fails(node_repo):
    _fake_tsc(node_repo, 2)
    stage(node_repo, "src/a.ts")
    result = run_guard(GUARD, node_repo, message=None)
    assert result.returncode == BLOCKED
    assert "[BLOCK] TypeScript errors" in result.stderr
    assert "error TS2322" in result.stderr


@posix_only
def test_should_pass_when_tsc_succeeds(node_repo):
    _fake_tsc(node_repo, 0)
    stage(node_repo, "src/a.tsx")
    result = run_guard(GUARD, node_repo, message=None)
    assert result.returncode == 0, result.stderr
    assert "TypeScript OK" in result.stdout


@posix_only
def test_should_skip_failing_tsc_when_no_ts_or_js_file_is_staged(node_repo):
    _fake_tsc(node_repo, 2)
    stage(node_repo, "docs/SETUP.md")
    result = run_guard(GUARD, node_repo, message=None)
    assert result.returncode == 0
    assert "skipped (no TS/JS files staged)" in result.stdout


def test_should_warn_and_pass_when_tsc_is_not_installed(node_repo):
    stage(node_repo, "src/a.ts")
    result = run_guard(GUARD, node_repo, message=None)
    assert result.returncode == 0
    assert "[WARN] tsc not found" in result.stdout


@posix_only
def test_should_do_nothing_outside_a_node_project(repo):
    _fake_tsc(repo, 2)
    stage(repo, "src/a.ts")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""
