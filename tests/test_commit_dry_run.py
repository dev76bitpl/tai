"""Tests for scripts/commit-dry-run.py — the dry run sees the Claude Code hooks too (#135).

The old dry run ran only the pre-commit commit-msg stage, so it was green while a PreToolUse
hook (guard-ai-template) blocked the real `git commit` a moment later.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "commit-dry-run.py"


def _load():
    spec = importlib.util.spec_from_file_location("commit_dry_run", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def _settings(hooks: list[str], matcher: str = "Bash|PowerShell") -> dict:
    return {"hooks": {"PreToolUse": [{"matcher": matcher, "hooks": [
        {"type": "command", "command": f"python3 ${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{h}"} for h in hooks]}]}}


@pytest.fixture
def project(tmp_path):
    """A project (not the template) with the real hooks and guard-ai-template wired."""
    root = tmp_path / "project"
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for src in (ROOT / ".claude" / "hooks").glob("*.py"):
        shutil.copy(src, hooks / src.name)
    (hooks / "config.json").write_text(json.dumps({"ai_template_path": "/somewhere/template"}), encoding="utf-8")
    (root / ".claude" / "settings.local.json").write_text(json.dumps(_settings(["guard-ai-template.py"])),
                                                          encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "scripts").mkdir()
    (root / "scripts" / "tool.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "scripts/tool.py"], check=True)
    return root


def _message(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "MSG"
    path.write_text(text, encoding="utf-8")
    return path


def test_should_report_the_hook_that_blocks_the_real_commit(project, tmp_path, capsys):
    # the case from #135: a generic file staged, no [no-template] / [template-done]
    assert mod.dry_run(project, _message(tmp_path, "chore: tool\n"), with_pre_commit=False) is False
    out = capsys.readouterr().out
    assert "❌ guard-ai-template" in out and "Ocena AI template repo" in out
    assert "Something blocks" in out


def test_should_be_green_when_the_message_answers_the_hook(project, tmp_path, capsys):
    assert mod.dry_run(project, _message(tmp_path, "chore: tool\n\n[no-template]\n"), with_pre_commit=False) is True
    assert "✅ guard-ai-template" in capsys.readouterr().out


def test_should_read_the_hooks_wired_for_shell_commands_only(tmp_path):
    root = tmp_path / "r"
    (root / ".claude" / "hooks").mkdir(parents=True)
    for name in ("guard-a.py", "guard-b.py"):
        (root / ".claude" / "hooks" / name).write_text("", encoding="utf-8")
    settings = _settings(["guard-a.py", "missing.py"])
    settings["hooks"]["PreToolUse"] += _settings(["guard-b.py"], matcher="Edit|Write")["hooks"]["PreToolUse"]
    (root / ".claude" / "settings.local.json").write_text(json.dumps(settings), encoding="utf-8")
    assert mod.shell_hooks(root) == [root / ".claude" / "hooks" / "guard-a.py"]


def test_should_fall_back_to_the_shipped_example_when_nothing_is_wired(tmp_path):
    root = tmp_path / "r"
    (root / ".claude" / "hooks").mkdir(parents=True)
    (root / ".claude" / "hooks" / "guard-a.py").write_text("", encoding="utf-8")
    (root / ".claude" / "settings.local.json.example").write_text(json.dumps(_settings(["guard-a.py"])),
                                                                  encoding="utf-8")
    assert mod.shell_hooks(root) == [root / ".claude" / "hooks" / "guard-a.py"]


def test_should_say_when_pre_commit_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "pre_commit_command", lambda: None)
    passes, said = mod.run_commit_msg_stage(tmp_path, _message(tmp_path, "x\n"))
    assert passes is False and "pre-commit is not installed" in said


def test_should_exit_2_without_a_message_file(tmp_path):
    done = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "nope")], capture_output=True, text=True)
    assert done.returncode == 2 and "No message file" in done.stderr
