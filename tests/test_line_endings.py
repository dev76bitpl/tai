"""Tests for the line-ending setup of the template and of a freshly started project.

The template had no .gitattributes; the only protection was core.autocrlf=input set by
`npm install`, which the guided start never runs. A Windows clone then shows hundreds of files
as modified with no change in content and fights the line-ending guard on every commit.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES = ROOT / ".gitattributes"


def test_should_ship_a_repo_level_rule_for_line_endings():
    lines = [line.strip() for line in ATTRIBUTES.read_text(encoding="utf-8").splitlines()]
    assert "* text=auto eol=lf" in lines


@pytest.mark.parametrize("path", ["README.md", "scripts/doctor.py", ".claude/hooks/stack.py", "docs/SETUP.md"])
def test_should_check_text_files_out_with_lf_everywhere(path):
    result = subprocess.run(["git", "check-attr", "eol", "--", path], cwd=ROOT, capture_output=True, text=True)
    assert result.stdout.strip().endswith("eol: lf"), result.stdout


@pytest.mark.parametrize("path, expected", [("logo.png", "binary: set"), ("run.cmd", "eol: crlf"), ("run.bat", "eol: crlf")])
def test_should_leave_binaries_alone_and_keep_crlf_for_windows_scripts(path, expected):
    attribute = expected.split(":")[0]
    result = subprocess.run(["git", "check-attr", attribute, "--", path], cwd=ROOT, capture_output=True, text=True)
    assert result.stdout.strip().endswith(expected), result.stdout


def test_should_not_keep_any_crlf_file_in_the_repository():
    # with the rule in place a CRLF file in the index would show as modified in every clone
    result = subprocess.run(["git", "ls-files", "--eol"], cwd=ROOT, capture_output=True, text=True)
    assert [line for line in result.stdout.splitlines() if line.startswith(("i/crlf", "i/mixed"))] == []


def test_should_say_in_setup_hooks_what_really_protects_the_clone():
    script = (ROOT / "scripts" / "setup-hooks.mjs").read_text(encoding="utf-8")
    assert ".gitattributes" in script and ATTRIBUTES.is_file()  # the comment used to point at a missing file


# ── messages must not send people to places that do not exist (#174) ─────────

GUARDS = ROOT / "docs" / "GUARDS.md"
SCRIPT_FILES = [*ROOT.glob("scripts/*.py"), *ROOT.glob("scripts/*.mjs"), *ROOT.glob("scripts/dev-guards/*.py"),
                *ROOT.glob(".claude/hooks/*.py")]


def _guards_sections() -> set[str]:
    return set(re.findall(r"^#{2,3} (.+)$", GUARDS.read_text(encoding="utf-8"), flags=re.M))


def _section_references() -> list[tuple[str, str]]:
    found = []
    for path in SCRIPT_FILES:
        text = path.read_text(encoding="utf-8").replace('\\"', '"')
        for match in re.finditer(r'GUARDS\.md, (?:sekcja|section) [„"]([^”"]+)[”"]', text):
            found.append((path.name, match.group(1)))
    return found


def test_should_find_section_references_to_check():
    assert len(_section_references()) >= 5


@pytest.mark.parametrize("source, name", _section_references())
def test_should_point_messages_only_at_guards_sections_that_exist(source, name):
    assert name in _guards_sections(), f"{source} refers to docs/GUARDS.md section {name!r}, which does not exist"


@pytest.mark.parametrize("path", SCRIPT_FILES, ids=lambda p: p.name)
def test_should_not_refer_to_numbered_setup_steps_from_scripts(path):
    # numbers drift when a step is added; messages name a section of docs/GUARDS.md instead
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"SETUP\.md,? (?:step|krok) \d", text)
