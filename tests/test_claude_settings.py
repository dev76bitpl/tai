"""Tests for scripts/claude_settings.py — every checkout, a new worktree included, gets the file
that wires the Claude Code hooks (#260).

Before: only the project start wrote .claude/settings.local.json, so `git worktree add` gave a
directory where no Claude Code hook ran at all and only the pre-commit guards were left.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "claude_settings.py"


def _load():
    spec = importlib.util.spec_from_file_location("claude_settings", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
EXAMPLE = '{"command": "INTERPRETER ${CLAUDE_PROJECT_DIR}/.claude/hooks/guard-x.py"}'


def _with_example(root: Path) -> Path:
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "settings.local.json.example").write_text(EXAMPLE, encoding="utf-8")
    return root


@pytest.mark.parametrize("platform,command", [("linux", "python3"), ("darwin", "python3"), ("win32", "py")])
def test_should_create_the_file_with_this_machines_python(tmp_path, platform, command):
    root = _with_example(tmp_path)
    with mock.patch("sys.platform", platform):
        assert mod.ensure_settings_local(root) == ("created", [])
    text = (root / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    assert f'"{command} ${{CLAUDE_PROJECT_DIR}}' in text and "INTERPRETER" not in text


def test_should_leave_an_existing_file_alone_when_nothing_is_missing(tmp_path):
    root = _with_example(tmp_path)
    (root / ".claude" / "settings.local.json").write_text('{"mine": true}', encoding="utf-8")
    assert mod.ensure_settings_local(root) == ("present", [])
    assert (root / ".claude" / "settings.local.json").read_text(encoding="utf-8") == '{"mine": true}'


def test_should_leave_an_unreadable_file_alone(tmp_path):
    root = _project(tmp_path, "session-context.py")
    (root / ".claude" / "settings.local.json").write_text("{broken", encoding="utf-8")
    assert mod.ensure_settings_local(root) == ("unreadable", [])
    assert (root / ".claude" / "settings.local.json").read_text(encoding="utf-8") == "{broken"


# #268: a project with its own settings.local.json from before the template never ran
# session-context.py, so its session start never said the template had changes.
REAL_EXAMPLE = (ROOT / ".claude" / "settings.local.json.example").read_text(encoding="utf-8")
OWN = {
    "permissions": {"allow": ["Bash(npm test)"]},
    "hooks": {
        "PostToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [
            {"type": "command", "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/help-source-signal.py"}]}],
        "PreToolUse": [{"matcher": "Bash|PowerShell", "hooks": [
            {"type": "command", "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/guard-process-kill.py"}]}],
    },
}
TEMPLATE_HOOKS = ["session-context.py", "guard-process-kill.py", "guard-ai-template.py",
                  "guard-template-sync.py", "guard-testing-checklist.py", "suggest-pr.py"]


def _project(root: Path, *scripts: str) -> Path:
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "settings.local.json.example").write_text(REAL_EXAMPLE, encoding="utf-8")
    for name in scripts:
        (hooks / name).write_text("", encoding="utf-8")
    return root


def _commands(settings: dict, event: str) -> "list[str]":
    return [h["command"] for g in settings["hooks"].get(event, []) for h in g["hooks"]]


def test_should_add_the_template_hooks_an_own_file_lacks(tmp_path):
    root = _project(tmp_path, "help-source-signal.py", *TEMPLATE_HOOKS)
    target = root / ".claude" / "settings.local.json"
    target.write_text(json.dumps(OWN), encoding="utf-8")
    with mock.patch("sys.platform", "linux"):
        state, added = mod.ensure_settings_local(root)
    assert state == "updated"
    assert sorted(added) == sorted(set(TEMPLATE_HOOKS) - {"guard-process-kill.py"})
    settings = json.loads(target.read_text(encoding="utf-8"))
    assert settings["permissions"] == OWN["permissions"]
    assert _commands(settings, "UserPromptSubmit") == ["python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/session-context.py"]
    pre = _commands(settings, "PreToolUse")
    assert pre.count("python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/guard-process-kill.py") == 1
    assert len(settings["hooks"]["PreToolUse"]) == 1 and len(pre) == 4  # same matcher: one group
    post = settings["hooks"]["PostToolUse"]
    assert post[0] == OWN["hooks"]["PostToolUse"][0]  # the project's own hook is untouched
    assert post[1]["matcher"] == "Bash|PowerShell" and _commands({"hooks": {"x": post[1:]}}, "x") == [
        "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/suggest-pr.py"]
    assert "INTERPRETER" not in target.read_text(encoding="utf-8")


def test_should_add_nothing_the_second_time(tmp_path):
    root = _project(tmp_path, *TEMPLATE_HOOKS)
    (root / ".claude" / "settings.local.json").write_text(json.dumps(OWN), encoding="utf-8")
    mod.ensure_settings_local(root)
    before = (root / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    assert mod.ensure_settings_local(root) == ("present", [])
    assert (root / ".claude" / "settings.local.json").read_text(encoding="utf-8") == before


def test_should_not_wire_a_hook_whose_script_the_project_does_not_have(tmp_path):
    root = _project(tmp_path, "session-context.py")
    (root / ".claude" / "settings.local.json").write_text(json.dumps(OWN), encoding="utf-8")
    assert mod.ensure_settings_local(root) == ("updated", ["session-context.py"])


def test_should_not_add_a_hook_already_wired_in_the_shared_settings(tmp_path):
    root = _project(tmp_path, "session-context.py")
    (root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
        {"type": "command", "command": "py ${CLAUDE_PROJECT_DIR}/.claude/hooks/session-context.py"}]}]}}),
        encoding="utf-8")
    (root / ".claude" / "settings.local.json").write_text(json.dumps(OWN), encoding="utf-8")
    assert mod.ensure_settings_local(root) == ("present", [])


def test_should_wire_the_hooks_after_a_template_update(tmp_path):
    source = (ROOT / "scripts" / "update-from-template.py").read_text(encoding="utf-8")
    assert "run_after_apply(ROOT, applied)" in source and "claude_settings.py" in source


def test_should_do_nothing_without_the_example(tmp_path):
    assert mod.ensure_settings_local(tmp_path) == ("no-example", [])
    assert not (tmp_path / ".claude" / "settings.local.json").exists()


def test_should_never_fail_a_checkout(tmp_path):
    copy = tmp_path / "scripts"
    copy.mkdir()
    shutil.copy(SCRIPT, copy / SCRIPT.name)  # no .claude/ at all next to it
    assert subprocess.run([sys.executable, str(copy / SCRIPT.name)]).returncode == 0


def test_should_be_wired_as_a_post_checkout_hook_installed_by_default():
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "default_install_hook_types: [pre-commit, commit-msg, post-checkout]" in config
    assert "entry: python3 scripts/claude_settings.py" in config
    assert "stages: [post-checkout]" in config


@pytest.mark.parametrize("path", ["scripts/setup-hooks.mjs", "scripts/new_project_git.py", "scripts/doctor.py"])
def test_should_install_the_post_checkout_hook_wherever_hooks_are_installed(path):
    assert "post-checkout" in (ROOT / path).read_text(encoding="utf-8")


def _pre_commit() -> "list[str] | None":
    if shutil.which("pre-commit"):
        return ["pre-commit"]
    probe = subprocess.run([sys.executable, "-m", "pre_commit", "--version"], capture_output=True)
    return [sys.executable, "-m", "pre_commit"] if probe.returncode == 0 else None


@pytest.mark.skipif(_pre_commit() is None, reason="pre-commit not installed")
def test_should_wire_the_hooks_in_a_new_worktree_end_to_end(tmp_path):
    repo = tmp_path / "repo"
    for rel in ("scripts/claude_settings.py", ".pre-commit-config.yaml", ".claude/settings.local.json.example"):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, repo / rel)
    git = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "init", "--no-verify"], check=True)
    subprocess.run([*_pre_commit(), "install", "--hook-type", "post-checkout"], cwd=repo, check=True,
                   capture_output=True)
    subprocess.run([*git, "worktree", "add", "-q", str(tmp_path / "wt"), "-b", "work"], check=True,
                   capture_output=True)
    settings = json.loads((tmp_path / "wt" / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    assert "INTERPRETER" not in json.dumps(settings) and "hooks" in settings
