#!/usr/bin/env python3
"""
Autodetekcja stacku i komendy lint/test.

Kolejność rozstrzygania (stack):
1. .claude/hooks/config.json + config.local.json (override projektu / maszyny)
2. Autodetekcja na podstawie plików w repo
3. Nieznany stack → ostrzeżenie, brak blokowania

Kolejność rozstrzygania (ścieżka do template — resolve_template_source):
1. $AI_TEMPLATE_PATH        — jeden export na maszynę, obsługuje wszystkie projekty
2. config.local.json        — per-klon, gitignored
3. config.json              — commitowany (opcjonalny)
4. autodetekcja klona obok  — po markerze is_template, nigdy po nazwie katalogu
5. DEFAULT_TEMPLATE_URL     — działa bez żadnej konfiguracji

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
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_TEMPLATE_URL = "https://github.com/dev76bitpl/tai.git"
_TEMPLATE_URL_PREFIXES = ("http://", "https://", "git@", "ssh://")

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
    """Extract target directory from git -C /path or cd /path && / cd /path; patterns."""
    import re
    m = re.search(r"git\s+-C\s+([^\s]+)", command)
    if m:
        return m.group(1)
    # Handle both && and ; separators; strip surrounding quotes from path
    m = re.search(r"cd\s+([^\s\"']+|\"[^\"]+\"|'[^']+')\s*(?:&&|;)", command)
    if m:
        return m.group(1).strip("\"'")
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
    """config.json + config.local.json (per-maszyna, gitignored) — local nadpisuje."""
    hooks_dir = Path(__file__).resolve().parent
    config: dict = {}
    for name in ("config.json", "config.local.json"):
        path = hooks_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            config.update(data)
    return config


def is_template_url(value: str) -> bool:
    return value.startswith(_TEMPLATE_URL_PREFIXES)


def _is_template_root(path: Path) -> bool:
    """Klon template rozpoznawany po zawartosci, nie po nazwie.

    Repo bylo juz przemianowane (ai -> tai), a katalog na dysku moze nazywac sie
    dowolnie — dopasowanie po nazwie rozwala sie przy kazdej takiej zmianie.
    Markerem jest is_template: true w jego wlasnym configu + skills-manifest.json.
    """
    try:
        if not (path / "skills-manifest.json").is_file():
            return False
        config_path = path / ".claude" / "hooks" / "config.json"
        if not config_path.is_file():
            return False
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return isinstance(data, dict) and data.get("is_template") is True


def _autodetect_template_root() -> Path | None:
    """Szuka klona template wsrod rodzenstwa katalogu projektu."""
    project_root = get_hooks_root()
    try:
        siblings = sorted(project_root.parent.iterdir())
    except Exception:
        return None
    for candidate in siblings:
        if candidate == project_root or not candidate.is_dir():
            continue
        if _is_template_root(candidate):
            return candidate
    return None


def resolve_template_source(config: dict | None = None) -> tuple[str, str]:
    """Zwraca (wartosc, zrodlo) sciezki/URL template.

    Kolejnosc: $AI_TEMPLATE_PATH > config.local.json > config.json >
    autodetekcja klona obok > DEFAULT_TEMPLATE_URL.

    Dzieki temu zaden klon nie wymaga wpisywania sciezki z konkretnej maszyny
    do commitowanego configu: jeden export w ~/.bashrc obsluguje wszystkie
    projekty, a bez niego dziala publiczny URL template.
    """
    env_value = os.environ.get("AI_TEMPLATE_PATH", "").strip()
    if env_value:
        return env_value, "$AI_TEMPLATE_PATH"

    cfg = load_config() if config is None else config
    cfg_value = str(cfg.get("ai_template_path", "") or "").strip()
    if cfg_value:
        return cfg_value, "config.json"

    detected = _autodetect_template_root()
    if detected:
        return str(detected), "autodetekcja"

    return DEFAULT_TEMPLATE_URL, "default"


def resolve_template_path(config: dict | None = None) -> str:
    return resolve_template_source(config)[0]


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
    - `cd /path; git commit ...`          ← PowerShell uses ; not &&
    - `git add X && git commit ...`
    - `git add X; git commit ...`         ← PowerShell chained
    - `cd /path; git add X; git commit`   ← PowerShell multi-step

    Non-acceptable: anything starting with `gh`, `npm`, `echo`, etc., even
    if their arguments contain the literal text `git commit`.
    """
    import re
    # Fast path: must contain git commit at all
    if not re.search(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b", command):
        return False
    # git commit must appear as a top-level shell token — after ^, &&, ;, or |
    # (not buried inside a string argument of another command like gh/npm/echo)
    return bool(re.search(
        r"(?:^|&&|;|\|)\s*(?:cd\s+\S+\s*(?:&&|;)\s*)?git\s+(?:-C\s+\S+\s+)?commit\b",
        command,
        re.MULTILINE,
    ))


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
            pending_adds.append(token.strip("\"'"))

    # Dedup while preserving order
    return list(dict.fromkeys(staged + pending_adds))


def _inline_commit_message(command: str) -> str | None:
    """Commit message passed inline: -m "...", bash heredoc, or PowerShell here-string."""
    m = re.search(r'-m\s+"([^"]+)"', command) or re.search(r"-m\s+'([^']+)'", command)
    if m:
        return m.group(1)
    # bash heredoc: ... <<'EOF' ... EOF  (any word delimiter)
    m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?\s*\n(.*?)\n\1\b", command, re.DOTALL)
    if m:
        return m.group(2)
    # PowerShell here-string: -m @'\n...\n'@  or  @"\n...\n"@
    m = re.search(r"-m\s+@['\"]\s*\n(.*?)\n['\"]@", command, re.DOTALL)
    if m:
        return m.group(1)
    return None


def _file_commit_message(command: str) -> str | None:
    """Commit message from a file: -F <path> / --file <path> / --file=<path>."""
    m = re.search(r"(?:-F|--file)(?:=|\s+)(\S+)", command)
    if not m:
        return None
    path = m.group(1).strip("\"'")
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def get_commit_message(command: str) -> str | None:
    """Best-effort full commit message from inline (-m/heredoc/here-string) or file (-F).

    Shared by PreToolUse guards that must see bypass flags regardless of how the
    message reaches git — inline flags live in the command string, but `-F <file>`
    keeps them in a file the command only references. Without reading the file a
    flag check on the bare command silently misses `[skip-sync]` / `[no-template]`.
    """
    return _inline_commit_message(command) or _file_commit_message(command)
