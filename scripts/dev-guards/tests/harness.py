"""Shared harness for the commit-guard tests: a real git repository in a temp directory,
the guards copied into it, each guard run as a separate process.

Why end to end: pre-commit blocks a commit on the guard's exit code, so that is what the
tests assert. A test that only calls an inner function stays green when the guard is broken
into "always exit 0".

Why a copy of the guards: they read .claude/hooks/config.json relative to their own file.
Running the copy keeps the tests independent of this repository's own config.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

GUARDS = Path(__file__).resolve().parents[1]
BLOCKED = 1  # pre-commit treats any non-zero code as a block; the guards use exactly 1


def clean_env(**extra: str) -> dict:
    """The environment without the variables git sets inside a hook — the suite itself runs
    from a pre-commit hook, and GIT_INDEX_FILE would point every temp repo at the real index."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(extra)
    return env


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, env=clean_env(), check=True,
                            capture_output=True, text=True, encoding="utf-8")
    return result.stdout


def make_repo(root: Path, branch: str = "main", config: dict | None = None) -> Path:
    """An empty repository on `branch` (no commits yet) with the guards installed."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    git(root, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "commit.gpgsign", "false")
    dest = root / "scripts" / "dev-guards"
    dest.mkdir(parents=True)
    for src in GUARDS.glob("*.py"):
        shutil.copy(src, dest / src.name)
    if config is not None:
        write_config(root, config)
    return root


def write_config(repo: Path, config: dict) -> None:
    path = repo / ".claude" / "hooks" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config), encoding="utf-8")


def stage(repo: Path, name: str, text: str = "x\n") -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    git(repo, "add", "--", name)


def commit(repo: Path, message: str = "chore: commit") -> None:
    git(repo, "commit", "-q", "--no-verify", "-m", message)


def run_guard(guard: str, repo: Path, message: str | None = "chore: something\n",
              cwd: Path | None = None, **env: str) -> subprocess.CompletedProcess:
    """Run scripts/dev-guards/<guard>.py from the repo's own copy.

    message=None runs the guard with no commit message file argument (pre-commit stage, or the
    "message did not arrive" case for a commit-msg guard)."""
    args = [sys.executable, str(repo / "scripts" / "dev-guards" / f"{guard}.py")]
    if message is not None:
        msg_file = repo / ".git" / "COMMIT_EDITMSG"
        msg_file.parent.mkdir(parents=True, exist_ok=True)
        msg_file.write_text(message, encoding="utf-8")
        args.append(str(msg_file))
    return subprocess.run(args, cwd=cwd or repo, env=clean_env(**env),
                          capture_output=True, text=True, encoding="utf-8")
