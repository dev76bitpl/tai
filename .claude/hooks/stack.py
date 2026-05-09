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


def get_project_root() -> str:
    """Returns absolute path to git project root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def chdir_to_project_root() -> None:
    """CD to project root so all relative paths work regardless of CWD."""
    import os
    import sys
    root = get_project_root()
    if root:
        os.chdir(root)
        # Ensure hooks dir is on path for imports
        hooks_dir = os.path.join(root, ".claude", "hooks")
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)


def load_config() -> dict:
    config_path = Path(".claude/hooks/config.json")
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
