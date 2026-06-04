#!/usr/bin/env python3
"""Shared utilities for dev-guards hooks.

Invoked by pre-commit framework (https://pre-commit.com). pre-commit handles
hook invocation, staged-file resolution, and exit-code propagation — the
guards just need stack detection + git helpers + config loading.

Resolution order for lint/test commands:
  1. .claude/hooks/config.json (project-level override, optional)
  2. Autodetection based on repo marker files
  3. Unknown stack → warn, do not block

Config file is canonical (ADR-002): the same .claude/hooks/config.json read by
.claude/hooks/stack.py, doctor.py and session-context.py. The old orphan
.pre-commit-hooks.config.json had no producer, leaving these guards dead.
"""
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = REPO_ROOT / ".claude" / "hooks" / "config.json"

STACKS: dict[str, dict] = {
    "node": {
        "markers": ["package.json"],
        "lint": ["npm", "run", "lint", "--silent"],
        "test": ["npm", "test", "--", "--passWithNoTests", "--bail=1", "--silent"],
    },
    "php": {
        "markers": ["composer.json"],
        "lint": ["composer", "lint"],
        "test": ["composer", "test"],
    },
    "python": {
        "markers": ["requirements.txt", "pyproject.toml", "setup.py"],
        "lint": ["ruff", "check", "."],
        "test": ["pytest", "--tb=short", "-q"],
    },
    "ruby": {
        "markers": ["Gemfile"],
        "lint": ["rubocop"],
        "test": ["rspec"],
    },
    "go": {
        "markers": ["go.mod"],
        "lint": ["golangci-lint", "run"],
        "test": ["go", "test", "./..."],
    },
}

BASE_ADR_PATTERNS: list[tuple[str, str]] = [
    (r"package\.json$", "node dependency change"),
    (r"composer\.json$", "php dependency change"),
    (r"requirements\.txt$|pyproject\.toml$", "python dependency change"),
    (r"go\.mod$", "go dependency change"),
    (r"\.sql$", "database migration"),
    (r"prisma/schema\.prisma$", "Prisma schema change"),
    (r"src/app/api/.*route\.(ts|tsx)$", "new API endpoint"),
    (r"src/middleware\.(ts|tsx)$", "middleware/auth change"),
    (r"src/lib/auth/", "auth logic change"),
    (r"docker-compose", "infrastructure change"),
    (r"\.env(\.|$)", "environment variable change"),
    (r"\.htaccess$", "server configuration change"),
    (r"wp-config\.php$", "WordPress configuration change"),
    (r"nginx\.conf|apache.*\.conf", "server configuration change"),
]

SRC_EXTENSIONS = (".ts", ".tsx", ".php", ".py", ".rb", ".go", ".js", ".jsx")


def _normalize_git_path(path: str) -> str:
    """Convert /c/foo/bar (Git for Windows) to C:/foo/bar."""
    if platform.system() == "Windows":
        m = re.match(r"^/([a-zA-Z])/(.+)$", path)
        if m:
            return f"{m.group(1).upper()}:/{m.group(2)}"
    return path


def get_project_root() -> Path:
    """Returns the git project root as Path. Falls back to REPO_ROOT."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(_normalize_git_path(result.stdout.strip()))
    return REPO_ROOT


def load_config() -> dict:
    if CONFIG_PATH.is_file():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def detect_stack() -> str:
    root = get_project_root()
    for name, cfg in STACKS.items():
        if any((root / m).is_file() for m in cfg["markers"]):
            return name
    return "unknown"


def _str_to_cmd(s: str) -> list[str]:
    return s.split()


def get_lint_cmd() -> list[str] | None:
    config = load_config()
    if "lint" in config:
        return _str_to_cmd(config["lint"])
    stack = detect_stack()
    if stack == "unknown":
        return None
    return STACKS[stack]["lint"]


def get_test_cmd() -> list[str] | None:
    config = load_config()
    if "test" in config:
        return _str_to_cmd(config["test"])
    stack = detect_stack()
    if stack == "unknown":
        return None
    return STACKS[stack]["test"]


def get_adr_patterns() -> list[tuple[str, str]]:
    config = load_config()
    extra = [(p, d) for p, d in config.get("adr_patterns", [])]
    return BASE_ADR_PATTERNS + extra


def cmd_exists(cmd: list[str]) -> bool:
    try:
        subprocess.run([cmd[0], "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Run a command, return (returncode, last-3000-chars of combined output)."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd or get_project_root()),
    )
    output = (result.stdout + result.stderr)[-3000:]
    return result.returncode, output


def get_staged_files() -> list[str]:
    """Files currently staged for commit (relative to repo root)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines() if result.returncode == 0 else []


def get_current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def read_commit_msg(argv: list[str]) -> str:
    """commit-msg stage: pre-commit passes commit-msg file path as argv[1]."""
    if len(argv) < 2:
        return ""
    msg_path = Path(argv[1])
    if not msg_path.is_file():
        return ""
    try:
        return msg_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def block(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)
