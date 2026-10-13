"""Git steps of scripts/new-project.py: fresh history on main and guard installation.

Split out to keep new-project.py under the logic-file size limit. Also holds the two output
helpers (log, warn) so both files print alike. Template-only: removed by --init and not
copied in copy-to-dir mode (TEMPLATE_ONLY_SCRIPTS in new_project_data.py).
"""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from start_ui import BOLD, YELLOW, item, paint  # noqa: E402


def log(label: str, path: str, dry_run: bool) -> None:
    item(label, path, planned=dry_run)


def _on_rm_error(func, path, _exc_info) -> None:
    """rmtree onerror handler: clear read-only bit (Windows .git pack files) and retry."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def fresh_git_history(root: Path, dry_run: bool) -> None:
    """Replace the template's git history with a single init commit for the project.

    The new repo has no remote and no installed hooks yet, so the init commit is
    unguarded by design — guards apply once the user wires up origin and installs
    pre-commit (see next steps).
    """
    git_dir = root / ".git"
    log("rmdir", ".git  (template history)", dry_run)
    log("git", "init -b main", dry_run)
    log("git", 'commit -m "chore: initialize project from AI template"', dry_run)
    if dry_run:
        return
    if git_dir.exists():
        shutil.rmtree(git_dir, onerror=_on_rm_error)
    try:
        # -b main: the guards and the whole described workflow assume main, while a bare
        # `git init` follows the machine's init.defaultBranch and may start on master
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(root), check=True)
        # same setting scripts/setup-hooks.mjs makes on `npm install` — the guided start does not
        # run npm, so without this a Windows clone would start with core.autocrlf=true
        subprocess.run(["git", "config", "--local", "core.autocrlf", "input"], cwd=str(root), check=True)
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "chore: initialize project from AI template"],
            cwd=str(root), check=True,
        )
    except subprocess.CalledProcessError as exc:
        warn(
            f"git init/commit failed (exit {exc.returncode}). "
            "Cleaning is done; finish git manually:\n"
            "    git init -b main && git add -A && "
            'git commit -m "chore: initialize project from AI template"'
        )


def warn(msg: str) -> None:
    sys.stdout.flush()
    print(f"  {paint('⚠', YELLOW, BOLD)} {msg}", file=sys.stderr)


def _resolve_pre_commit() -> list[str] | None:
    """argv prefix to invoke pre-commit — standalone binary or `python -m pre_commit`.

    Falls back to the module form because on Windows `pip install --user` often
    leaves the binary off PATH while `python -m pre_commit` still works.
    """
    if shutil.which("pre-commit"):
        return ["pre-commit"]
    for py in ("python", "python3", "py"):
        if not shutil.which(py):
            continue
        probe = subprocess.run(
            [py, "-m", "pre_commit", "--version"], capture_output=True
        )
        if probe.returncode == 0:
            return [py, "-m", "pre_commit"]
    return None


def install_guards(root: Path, dry_run: bool) -> None:
    """Install pre-commit + commit-msg git hooks so the project is guarded from commit #1.

    Runs after the init commit (the fresh repo defaults to branch main, where
    no-commit-to-branch would otherwise block a guarded init commit). Soft-fails:
    a missing pre-commit warns with the manual command instead of aborting init.
    """
    log("git-hooks", "pre-commit install (pre-commit + commit-msg)", dry_run)
    if dry_run:
        return
    invocation = _resolve_pre_commit()
    if invocation is None:
        warn(
            "pre-commit not found — guards not installed. Install later with:\n"
            "    npm install   (or: pre-commit install "
            "--hook-type pre-commit --hook-type commit-msg)"
        )
        return
    result = subprocess.run(
        [*invocation, "install", "--hook-type", "pre-commit", "--hook-type", "commit-msg"],
        cwd=str(root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        warn(f"pre-commit install failed: {result.stderr.strip()[:300]}")
