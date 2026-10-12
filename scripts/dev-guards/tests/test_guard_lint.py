"""Tests for scripts/dev-guards/guard_lint.py — the project's lint command gates the commit.

The lint command comes from .claude/hooks/config.json, so the tests point it at tiny scripts
that pass or fail on purpose; no real linter is needed.
"""
from harness import BLOCKED, run_guard, stage, write_config

GUARD = "guard_lint"


def _lint_script(repo, name, code):
    (repo / name).write_text(code, encoding="utf-8")
    write_config(repo, {"lint": f"python3 {name}"})


def test_should_block_and_show_output_when_lint_fails(repo):
    _lint_script(repo, "lint.py", "import sys\nprint('E501 line too long')\nsys.exit(3)\n")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "[BLOCK] Lint failed" in result.stderr
    assert "E501 line too long" in result.stderr


def test_should_pass_when_lint_succeeds(repo):
    _lint_script(repo, "lint.py", "print('all good')\n")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0, result.stderr
    assert "Lint [unknown] OK" in result.stdout


def test_should_run_lint_from_the_project_root(repo):
    _lint_script(repo, "lint.py", "import os, sys\nsys.exit(0 if os.path.exists('lint.py') else 9)\n")
    (repo / "sub").mkdir()
    assert run_guard(GUARD, repo, message=None, cwd=repo / "sub").returncode == 0


def test_should_warn_and_pass_when_stack_is_unknown(repo):
    # no config, no marker file: nothing to run. Documented behaviour — warn, do not block.
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0
    assert "[WARN] Unknown stack" in result.stdout


def test_should_warn_and_pass_when_lint_command_is_not_installed(repo):
    # an external tool that is not there is "could not check for reasons outside the repo"
    write_config(repo, {"lint": "no-such-linter-xyz --check"})
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0
    assert "[WARN] Lint command unavailable: no-such-linter-xyz --check" in result.stdout


def test_should_prefer_config_over_autodetected_stack(repo):
    stage(repo, "package.json", "{}\n")  # would autodetect node and run npm
    _lint_script(repo, "lint.py", "import sys\nsys.exit(1)\n")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "[BLOCK] Lint failed" in result.stderr


# ── config.local.json (per machine) overrides config.json ────────────────────

def test_should_use_lint_command_from_local_config_when_it_overrides_shared(repo):
    (repo / "pass.py").write_text("print('shared')\n", encoding="utf-8")
    (repo / "fail.py").write_text("import sys\nprint('from local')\nsys.exit(1)\n", encoding="utf-8")
    write_config(repo, {"lint": "python3 pass.py"})
    write_config(repo, {"lint": "python3 fail.py"}, name="config.local.json")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "from local" in result.stderr


def test_should_use_lint_command_when_set_only_in_local_config(repo):
    (repo / "fail.py").write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
    write_config(repo, {"lint": "python3 fail.py"}, name="config.local.json")
    assert run_guard(GUARD, repo, message=None).returncode == BLOCKED


def test_should_keep_shared_lint_command_when_local_config_is_unreadable(repo):
    _lint_script(repo, "lint.py", "import sys\nsys.exit(1)\n")
    (repo / ".claude" / "hooks" / "config.local.json").write_text("{ not json", encoding="utf-8")
    assert run_guard(GUARD, repo, message=None).returncode == BLOCKED
