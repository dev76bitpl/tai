"""Tests for scripts/dev-guards/guard_adr.py — architectural changes need an ADR or [no-adr]."""
import json
from pathlib import Path

import pytest

from harness import BLOCKED, run_guard, stage, write_config

GUARD = "guard_adr"


@pytest.mark.parametrize("path, reason", [
    ("package.json", "node dependency change"),
    ("db/001_init.sql", "database migration"),
    ("docker-compose.yml", "infrastructure change"),
    (".env.example", "environment variable change"),
    ("src/lib/auth/session.ts", "auth logic change"),
])
def test_should_block_when_architectural_file_is_staged_without_adr(repo, path, reason):
    stage(repo, path)
    result = run_guard(GUARD, repo)
    assert result.returncode == BLOCKED
    assert "[BLOCK] Architectural changes detected" in result.stderr
    assert path in result.stderr and reason in result.stderr


def test_should_pass_when_adr_is_staged_with_the_change(repo):
    stage(repo, "package.json")
    stage(repo, "docs/adr/ADR-007-new-dependency.md")
    result = run_guard(GUARD, repo)
    assert result.returncode == 0, result.stderr


def test_should_pass_when_no_adr_flag_is_in_message(repo):
    stage(repo, "package.json")
    assert run_guard(GUARD, repo, "chore: bump\n\n[no-adr] patch bump only\n").returncode == 0


@pytest.mark.parametrize("path", ["README.md", "src/components/Button.tsx", "docs/SETUP.md"])
def test_should_pass_when_no_architectural_file_is_staged(repo, path):
    stage(repo, path)
    result = run_guard(GUARD, repo)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_should_pass_when_nothing_is_staged(repo):
    assert run_guard(GUARD, repo).returncode == 0


def test_should_block_on_pattern_added_in_project_config(repo):
    write_config(repo, {"adr_patterns": [["migrations/", "database migration"]]})
    stage(repo, "migrations/0002_add_table.py")
    result = run_guard(GUARD, repo)
    assert result.returncode == BLOCKED
    assert "migrations/0002_add_table.py" in result.stderr


def test_should_block_when_commit_message_file_is_missing(repo):
    stage(repo, "README.md")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "guard_adr: no commit message file given" in result.stderr


def test_should_block_when_staged_files_cannot_be_listed(repo, tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    result = run_guard(GUARD, repo, cwd=outside)
    assert result.returncode == BLOCKED
    assert "cannot list staged files" in result.stderr


def test_should_block_on_pattern_added_in_local_config(repo):
    # config.local.json (per machine) is layered over config.json, as in the Claude Code hooks
    write_config(repo, {"lint": "true"})
    write_config(repo, {"adr_patterns": [["billing/", "billing rules change"]]}, name="config.local.json")
    stage(repo, "billing/invoice.py")
    result = run_guard(GUARD, repo)
    assert result.returncode == BLOCKED
    assert "billing rules change" in result.stderr


# ── the config a new project starts with: platform patterns are opt-in ───────

EXAMPLE = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "config.json.example"


def _example_config() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", [
    "modules/M4-guards/OUTLINE.md", "themes/notes.md", "override/readme.txt",
    "wp-content/plugins/demo/demo.php", "app/code/Vendor/Module/registration.php",
])
def test_should_pass_platform_looking_path_with_the_config_a_new_project_gets(repo, path):
    write_config(repo, _example_config())
    stage(repo, path)
    result = run_guard(GUARD, repo)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("platform, path, label", [
    ("PrestaShop", "modules/mymodule/mymodule.php", "nowy moduł PrestaShop"),
    ("WordPress", "wp-content/plugins/demo/demo.php", "nowy plugin WordPress"),
    ("Magento", "app/code/Vendor/Module/registration.php", "nowy moduł Magento"),
])
def test_should_block_platform_path_once_the_project_enables_its_group(repo, platform, path, label):
    config = _example_config()
    config["adr_patterns"] += config["_adr_patterns_optional"][platform]
    write_config(repo, config)
    stage(repo, path)
    result = run_guard(GUARD, repo)
    assert result.returncode == BLOCKED
    assert label in result.stderr


def test_should_still_block_generic_pattern_with_the_config_a_new_project_gets(repo):
    write_config(repo, _example_config())
    stage(repo, "migrations/2026_add_orders.py")
    assert run_guard(GUARD, repo).returncode == BLOCKED
