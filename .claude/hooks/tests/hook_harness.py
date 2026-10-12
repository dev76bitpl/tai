"""Shared harness for the hook tests: a real git repository in a temp directory with its own
copy of the hooks, each hook run as a separate process with a PreToolUse payload on stdin.

Claude Code blocks a tool call only on exit code 2 (1 is a non-blocking error), so the tests
assert the exact code. The hooks are copied because they read config.json from their own
directory — the copy keeps the tests independent of this repository's config.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
BLOCKED = 2


def clean_env(**extra: str) -> dict:
    """Without the variables git sets inside a hook (the suite itself runs from pre-commit)
    and without a machine-wide template path."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "AI_TEMPLATE_PATH"}
    env.update(extra)
    return env


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, env=clean_env(), check=True,
                            capture_output=True, text=True, encoding="utf-8")
    return result.stdout


def make_project(root: Path, branch: str = "main", config: dict | None = None) -> Path:
    """An empty repository on `branch` (no commits yet) with the hooks installed."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    git(root, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "commit.gpgsign", "false")
    dest = root / ".claude" / "hooks"
    dest.mkdir(parents=True)
    for src in HOOKS.glob("*.py"):
        shutil.copy(src, dest / src.name)
    (dest / "config.json").write_text(json.dumps(config or {}), encoding="utf-8")
    return root


def stage(repo: Path, name: str, text: str = "x\n") -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    git(repo, "add", "--", name)


def commit(repo: Path, message: str = "chore: commit") -> None:
    git(repo, "commit", "-q", "--no-verify", "-m", message)


def run_hook(hook: str, repo: Path, command: str, tool_name: str | None = "Bash") -> subprocess.CompletedProcess:
    payload = {"tool_input": {"command": command}}
    if tool_name is not None:
        payload["tool_name"] = tool_name
    return subprocess.run(
        [sys.executable, str(repo / ".claude" / "hooks" / f"{hook}.py")],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        cwd=repo, env=clean_env(), capture_output=True,
    )


def stderr(result: subprocess.CompletedProcess) -> str:
    return result.stderr.decode("utf-8")
