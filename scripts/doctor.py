#!/usr/bin/env python3
"""Health check for developer environment.

Run: `npm run doctor` or `python scripts/doctor.py`

Reports prerequisites:
  - Python ≥ 3.9
  - Node ≥ 22
  - pre-commit installed + hooks linked into .git/hooks
  - .pre-commit-config.yaml present and parseable
  - ai_template_path configured in .claude/hooks/config.json (optional)
  - Docker running (optional but recommended)

Exit code 0 if all REQUIRED checks pass (optional checks may be ✗ without
failing the overall exit code). Exit code 1 if any required check fails.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Enable ANSI escape sequences on Windows 10+ terminals (cmd.exe, Windows Terminal).
if os.name == "nt":
    os.system("")

REPO_ROOT = Path(__file__).resolve().parent.parent

_USE_COLOR = sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"


def _c(code: str) -> str:
    return code if _USE_COLOR else ""


GREEN = _c("\033[32m")
RED = _c("\033[31m")
YELLOW = _c("\033[33m")
DIM = _c("\033[2m")
RESET = _c("\033[0m")


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str, hint: str = "") -> None:
    print(f"  {RED}✗{RESET} {msg}")
    if hint:
        print(f"    {DIM}{hint}{RESET}")


def warn(msg: str, hint: str = "") -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")
    if hint:
        print(f"    {DIM}{hint}{RESET}")


def header(msg: str) -> None:
    print(f"\n{msg}")


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode, (result.stdout + result.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1, ""


def check_python() -> bool:
    if sys.version_info < (3, 9):
        fail(
            f"Python {sys.version_info.major}.{sys.version_info.minor} — required: 3.9+",
            "Install Python 3.9 or newer.",
        )
        return False
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_node() -> bool:
    if not shutil.which("node"):
        fail("node not in PATH", "Install Node.js 22+ — see docs/SETUP.md step 1.")
        return False
    code, out = run(["node", "--version"])
    if code != 0:
        fail("node --version failed")
        return False
    version = out.lstrip("v").split(".")[0]
    try:
        major = int(version)
    except ValueError:
        warn(f"node version unrecognized: {out}")
        return True
    if major < 22:
        fail(f"node {out} — required: 22+", "Upgrade via nvm.")
        return False
    ok(f"node {out}")
    return True


_PRE_COMMIT_INVOCATION: list[str] | None = None


def _resolve_pre_commit() -> list[str] | None:
    """Returns the argv prefix needed to invoke pre-commit, or None if unavailable.

    Tries standalone binary first, then `python -m pre_commit` (works on Windows
    after `pip install --user` when Scripts/ isn't on PATH).
    """
    global _PRE_COMMIT_INVOCATION
    if _PRE_COMMIT_INVOCATION is not None:
        return _PRE_COMMIT_INVOCATION
    if shutil.which("pre-commit"):
        code, _ = run(["pre-commit", "--version"])
        if code == 0:
            _PRE_COMMIT_INVOCATION = ["pre-commit"]
            return _PRE_COMMIT_INVOCATION
    for py in ("python", "python3", "py"):
        if not shutil.which(py):
            continue
        code, _ = run([py, "-m", "pre_commit", "--version"])
        if code == 0:
            _PRE_COMMIT_INVOCATION = [py, "-m", "pre_commit"]
            return _PRE_COMMIT_INVOCATION
    return None


def check_pre_commit() -> bool:
    invocation = _resolve_pre_commit()
    if invocation is None:
        fail(
            "pre-commit not available",
            "Install via: python -m pip install --user pre-commit  (or rerun `npm install`)",
        )
        return False
    code, out = run([*invocation, "--version"])
    if code != 0:
        fail(f"{' '.join(invocation)} --version failed")
        return False
    via = "standalone" if invocation == ["pre-commit"] else f"via {' '.join(invocation[:-1])}"
    ok(f"{out}  ({via})")
    return True


def check_hooks_installed() -> bool:
    pre_commit_hook = REPO_ROOT / ".git" / "hooks" / "pre-commit"
    commit_msg_hook = REPO_ROOT / ".git" / "hooks" / "commit-msg"
    if not pre_commit_hook.is_file():
        fail(
            ".git/hooks/pre-commit not installed",
            "Run: pre-commit install --hook-type pre-commit --hook-type commit-msg",
        )
        return False
    if not commit_msg_hook.is_file():
        fail(
            ".git/hooks/commit-msg not installed",
            "Run: pre-commit install --hook-type commit-msg",
        )
        return False
    # Sanity check: pre-commit framework writes a marker line in its hook scripts.
    content = pre_commit_hook.read_text(encoding="utf-8", errors="ignore")
    if "pre-commit" not in content.lower():
        warn(
            ".git/hooks/pre-commit exists but doesn't look like pre-commit framework",
            "May be a stale hook — reinstall with: pre-commit install",
        )
        return False
    ok("Git hooks installed (pre-commit + commit-msg)")
    return True


def check_config_yaml() -> bool:
    config = REPO_ROOT / ".pre-commit-config.yaml"
    if not config.is_file():
        fail(".pre-commit-config.yaml missing at repo root")
        return False
    invocation = _resolve_pre_commit()
    if invocation is None:
        warn(".pre-commit-config.yaml not validated (pre-commit unavailable)")
        return False
    code, out = run([*invocation, "validate-config"])
    if code != 0:
        fail(".pre-commit-config.yaml invalid", out[-500:] if out else "")
        return False
    ok(".pre-commit-config.yaml valid")
    return True


def check_claude_template_path() -> None:
    config = REPO_ROOT / ".claude" / "hooks" / "config.json"
    if not config.is_file():
        warn(
            ".claude/hooks/config.json not configured (optional)",
            "Copy from config.json.example and set ai_template_path — see docs/SETUP.md.",
        )
        return
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        warn("config.json present but unparseable")
        return
    template = data.get("ai_template_path")
    if not template:
        warn("ai_template_path not set in .claude/hooks/config.json (optional)")
        return
    path = Path(template)
    if not path.is_dir():
        warn(
            f"ai_template_path doesn't exist: {template}",
            "AI template sync guard will skip silently.",
        )
        return
    ok(f"AI template repo: {template}")


def check_docker() -> None:
    if not shutil.which("docker"):
        warn("docker not in PATH (optional)", "Required to run the dev database.")
        return
    code, _ = run(["docker", "ps"])
    if code != 0:
        warn("docker installed but daemon not running")
        return
    ok("docker daemon running")


def check_git_branch() -> None:
    code, out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if code != 0:
        return
    branch = out.strip()
    if branch in ("main", "master"):
        warn(
            f"Currently on branch '{branch}'",
            "no-commit-to-branch will block commits. Switch via: git checkout -b feat/your-task",
        )
    else:
        ok(f"On branch: {branch}")


def main() -> int:
    print("Developer environment health check\n" + "=" * 35)

    required: list[bool] = []

    header("Prerequisites")
    required.append(check_python())
    required.append(check_node())

    header("Guard system")
    required.append(check_pre_commit())
    required.append(check_hooks_installed())
    required.append(check_config_yaml())

    header("Optional integrations")
    check_claude_template_path()
    check_docker()

    header("Repository state")
    check_git_branch()

    print()
    if all(required):
        print(f"{GREEN}All required checks passed.{RESET}")
        return 0
    failed_count = sum(1 for r in required if not r)
    print(f"{RED}{failed_count} required check(s) failed — see hints above.{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
