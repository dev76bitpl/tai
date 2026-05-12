#!/usr/bin/env python3
"""
Autodetekcja stacku i komendy lint/test.

Kolejność rozstrzygania:
1. .claude/hooks/config.json (override projektu)
2. Autodetekcja na podstawie plików w repo
3. Nieznany stack → ostrzeżenie, brak blokowania

config.json przykład:
{
  "lint": "composer lint",
  "test": "composer test",
  "adr_patterns": [
    ["migrations/", "migracja bazy danych"]
  ]
}
"""
import json
import platform
import re
import subprocess
from pathlib import Path

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

# ADR heurystyki — stack-agnostyczne + per-stack
BASE_ADR_PATTERNS: list[tuple[str, str]] = [
    (r"package\.json$", "zmiana zależności node"),
    (r"composer\.json$", "zmiana zależności php"),
    (r"requirements\.txt$|pyproject\.toml$", "zmiana zależności python"),
    (r"go\.mod$", "zmiana zależności go"),
    (r"\.sql$", "migracja bazy danych"),
    (r"prisma/schema\.prisma$", "zmiana schematu Prisma"),
    (r"src/app/api/.*route\.(ts|tsx)$", "nowy endpoint API"),
    (r"src/middleware\.(ts|tsx)$", "zmiana middleware/auth"),
    (r"src/lib/auth/", "zmiana logiki autoryzacji"),
    (r"docker-compose", "zmiana infrastruktury"),
    (r"\.env(\.|$)", "zmiana zmiennych środowiskowych"),
    (r"\.htaccess$", "zmiana konfiguracji serwera"),
    (r"wp-config\.php$", "zmiana konfiguracji WordPress"),
    (r"nginx\.conf|apache.*\.conf", "zmiana konfiguracji serwera"),
]


def _normalize_git_path(path: str) -> str:
    """Convert /c/foo/bar style paths (Git for Windows) to C:/foo/bar."""
    if platform.system() == "Windows":
        m = re.match(r"^/([a-zA-Z])/(.+)$", path)
        if m:
            return f"{m.group(1).upper()}:/{m.group(2)}"
    return path


def get_project_root() -> str:
    """Returns absolute path to git project root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return _normalize_git_path(result.stdout.strip()) if result.returncode == 0 else ""


def get_command_git_cwd(command: str) -> str | None:
    """Extract target directory from git -C /path or cd /path && patterns."""
    import re
    m = re.search(r"git\s+-C\s+([^\s]+)", command)
    if m:
        return m.group(1)
    m = re.search(r"cd\s+([^\s\"']+)\s+&&", command)
    if m:
        return m.group(1)
    return None


def is_foreign_repo(command: str) -> bool:
    """Return True if the git command targets a different repo than the current project."""
    git_cwd = get_command_git_cwd(command)
    if not git_cwd:
        return False
    project_root = get_project_root()
    from pathlib import Path
    try:
        return Path(git_cwd).resolve() != Path(project_root).resolve()
    except Exception:
        return False


def get_hooks_root() -> Path:
    """Returns the monorepo root — the directory that contains .claude/."""
    return Path(__file__).resolve().parent.parent.parent


def chdir_to_project_root(command: str = "") -> None:
    """CD to project root so all relative paths work regardless of CWD.

    When invoked from a monorepo root that is not itself a git repo,
    falls back to extracting the target repo path from the tool command
    (git -C <path> or cd <path> &&).
    Only follows paths that are inside the monorepo root — commands
    targeting external repos are left as-is so is_foreign_repo() catches them.
    """
    import os
    root = get_project_root()
    if not root and command:
        git_cwd = get_command_git_cwd(command)
        if git_cwd:
            hooks_root = get_hooks_root()
            try:
                if not Path(git_cwd).resolve().is_relative_to(hooks_root):
                    return
            except Exception:
                return
            candidate = subprocess.run(
                ["git", "-C", git_cwd, "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
            )
            if candidate.returncode == 0:
                root = candidate.stdout.strip()
    if root:
        os.chdir(root)


def load_config() -> dict:
    config_path = Path(__file__).resolve().parent / "config.json"
    if config_path.is_file():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def detect_stack() -> str:
    for name, cfg in STACKS.items():
        if any(Path(m).is_file() for m in cfg["markers"]):
            return name
    return "unknown"


def _str_to_cmd(s: str) -> list[str]:
    return s.split()


def get_lint_cmd() -> list[str] | None:
    """Returns lint command as list, or None if not available."""
    config = load_config()
    if "lint" in config:
        return _str_to_cmd(config["lint"])
    stack = detect_stack()
    if stack == "unknown":
        return None
    return STACKS[stack]["lint"]


def get_test_cmd() -> list[str] | None:
    """Returns test command as list, or None if not available."""
    config = load_config()
    if "test" in config:
        return _str_to_cmd(config["test"])
    stack = detect_stack()
    if stack == "unknown":
        return None
    return STACKS[stack]["test"]


def get_adr_patterns() -> list[tuple[str, str]]:
    """Returns ADR patterns: base + config overrides."""
    config = load_config()
    extra = [(p, d) for p, d in config.get("adr_patterns", [])]
    return BASE_ADR_PATTERNS + extra


def cmd_exists(cmd: list[str]) -> bool:
    """Check if the base command is available in PATH."""
    try:
        subprocess.run(
            [cmd[0], "--version"],
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    """Run command, return (returncode, combined output)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout + result.stderr)[-3000:]
    return result.returncode, output


def is_git_commit_command(command: str) -> bool:
    """
    Returns True if `command` actually invokes `git commit` (not just contains
    'git commit' as substring inside an argument string — e.g. `gh pr create
    --body "...git commit..."` should NOT match).

    Acceptable forms:
    - `git commit ...`
    - `git -C /path commit ...`
    - `cd /path && git commit ...`
    - `git add X && git commit ...`
    - heredoc forms starting with `git commit`

    Non-acceptable: anything starting with `gh`, `npm`, `echo`, etc., even
    if their arguments contain the literal text `git commit`.
    """
    import re
    stripped = command.strip()
    # First gate: command must start with `git` or `cd ... && git` (chained)
    if not re.match(r"^(?:cd\s+\S+\s*&&\s*)?git\b", stripped):
        return False
    # Second gate: a `git ... commit` invocation must appear (allows `git -C /path commit`)
    return bool(re.search(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b", command))


def get_staged_files(command: str = "") -> list[str]:
    """
    Returns currently staged files. If `command` is provided, also includes
    files about to be staged by `git add <files>` in the same chained command
    (e.g. `git add X && git commit Y`). PreToolUse hooks fire before the
    chain executes, so without this the hook would not see X as staged.

    Skips flag-only adds (-A, -u, --all) and wildcards (., *) — those would
    require ls-files lookup which is out of scope.
    """
    import re
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    )
    staged = result.stdout.splitlines() if result.returncode == 0 else []

    if not command:
        return staged

    pending_adds: list[str] = []
    for m in re.finditer(r"git\s+add\s+([^&|;]+)", command):
        args = m.group(1).strip()
        for token in args.split():
            if token.startswith("-"):
                continue
            if token in (".", "*"):
                continue
            pending_adds.append(token)

    # Dedup while preserving order
    return list(dict.fromkeys(staged + pending_adds))
