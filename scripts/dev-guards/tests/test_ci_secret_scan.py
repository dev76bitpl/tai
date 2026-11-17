"""Tests for the secret scan in .github/workflows/guards.yml.

Regression for a scan that could not fail: CI ran the gitleaks pre-commit hook through
`pre-commit run --all-files`, but the hook inspects STAGED files only and a CI checkout has an
empty index, so the step was green whatever the tree contained.

The workflow must scan the working tree in a step of its own, with the same gitleaks version the
local hook uses, and must not count the staged-only hook as coverage.

It lives next to the guards so it travels into every new project (#176): the workflow does, and
a project can bump the hook or rework the workflow and lose the scan with CI still green.
A project without GitHub Actions (no .github/ at all) skips it; once .github/ exists, a missing
guards.yml or scan step is a failure.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]  # scripts/dev-guards/tests -> repository root
if not (ROOT / ".github").is_dir():
    pytest.skip("no .github/ — this project does not use GitHub Actions", allow_module_level=True)
GUARDS_YML = ROOT / ".github" / "workflows" / "guards.yml"
assert GUARDS_YML.is_file(), ".github/ exists but .github/workflows/guards.yml with the secret scan is missing"
GUARDS = GUARDS_YML.read_text(encoding="utf-8")
PRE_COMMIT = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")


def _live_lines(text):
    """Workflow lines with comments dropped, so a commented-out step does not count."""
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def _scan_command():
    """The folded `docker run ... gitleaks ...` command as one string ('' when absent)."""
    lines = _live_lines(GUARDS)
    for i, line in enumerate(lines):
        if "docker run" in line:
            indent = len(line) - len(line.lstrip())
            block = [line.strip()]
            for following in lines[i + 1:]:
                if following.strip() and len(following) - len(following.lstrip()) < indent:
                    break
                block.append(following.strip())
            command = " ".join(block)
            if "gitleaks" in command:
                return command
    return ""


def _hook_version():
    match = re.search(r"repo:\s*https://github\.com/gitleaks/gitleaks\s*\n\s*rev:\s*(\S+)", PRE_COMMIT)
    assert match, "gitleaks hook not found in .pre-commit-config.yaml"
    return match.group(1)


def test_should_scan_working_tree_when_guards_workflow_runs():
    command = _scan_command()
    assert command, "guards.yml has no live step running the gitleaks image"
    assert " detect " in f" {command} "
    assert "--no-git" in command


def test_should_not_scan_staged_files_only_when_running_in_ci():
    command = _scan_command()
    assert "--staged" not in command
    assert " protect " not in f" {command} "


def test_should_use_hook_version_when_pinning_scan_image():
    match = re.search(r"gitleaks:(\S+)", _scan_command())
    assert match, "gitleaks image in guards.yml is not pinned to a tag"
    assert match.group(1) == _hook_version()


def test_should_keep_source_relative_when_scanning():
    # An absolute source puts the absolute path into fingerprints and .gitleaksignore stops matching.
    command = _scan_command()
    assert "-w /repo" in command
    assert "--source=." in command.split()


def test_should_skip_staged_only_hook_when_running_pre_commit_in_ci():
    skip = [line for line in _live_lines(GUARDS) if line.strip().startswith("SKIP:")]
    assert len(skip) == 1
    assert "gitleaks" in skip[0].split(":", 1)[1].strip().split(",")
