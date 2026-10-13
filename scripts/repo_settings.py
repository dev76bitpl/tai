"""GitHub repository settings a project from this template needs (docs/SETUP.md, step 1).

Shared by scripts/project-setup.py (the guided start sets them after asking) and
scripts/doctor.py (warns when they are still at GitHub's defaults). Both pass their own
`run(command) -> (exit code, output)`, so this module never starts a process itself.
Needs start_ui.py next to it (marks and colours of the step).

Two settings, of different weight:
  - delete the branch after merge        harmless; proposed for every project
  - Actions may write and approve PRs     needed by the release automation, which fails after
                                          every merge to main without it. A broader permission
                                          than a fresh repository has, so it is proposed only
                                          when the project actually has that automation.
"""
import re
from pathlib import Path

from start_ui import DIM, DONE, PENDING, SKIPPED, mark, notice, paint

DELETE_BRANCH = "delete_branch"
ACTIONS_WRITE = "actions_write"

LABELS = {
    DELETE_BRANCH: "kasowanie gałęzi po scaleniu",
    ACTIONS_WRITE: "uprawnienia automatów GitHuba: zapis do repo i zatwierdzanie pull requestów",
}
WHY = {
    DELETE_BRANCH: "bez tego gałęzie po każdym scaleniu trzeba sprzątać ręcznie",
    ACTIONS_WRITE: "bez tego automat wydań (release-please) kończy się błędem po każdym scaleniu do main",
}


def classify_repo_answer(answer: str) -> str:
    """'url' for an existing repository address, 'slug' for owner/name to create, else ''."""
    if "://" in answer or answer.startswith("git@") or answer.endswith(".git"):
        return "url"
    return "slug" if re.fullmatch(r"[\w.-]+/[\w.-]+", answer) else ""


def has_release_automation(root: Path) -> bool:
    workflows = root / ".github" / "workflows"
    return workflows.is_dir() and any(workflows.glob("release-please*.y*ml"))


def commands(slug: str) -> dict[str, list[str]]:
    """The gh call that applies each setting — also what the user is shown when GitHub refuses."""
    return {
        DELETE_BRANCH: ["gh", "api", "-X", "PATCH", f"repos/{slug}", "-F", "delete_branch_on_merge=true"],
        ACTIONS_WRITE: ["gh", "api", "-X", "PUT", f"repos/{slug}/actions/permissions/workflow",
                        "-f", "default_workflow_permissions=write", "-F", "can_approve_pull_request_reviews=true"],
    }


def repo_slug(run) -> tuple[str, str]:
    """(owner/name, '') for the connected GitHub repository, or ('', why not).

    Asks gh instead of reading the address: with an SSH host alias the URL has no "github.com".
    """
    code, output = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    if code == 127:
        return "", "brak polecenia `gh` (GitHub CLI)"
    if code != 0 or not output.strip():
        return "", "podpięte repo nie jest na GitHubie albo `gh` nie ma do niego dostępu"
    return output.strip(), ""


def read_state(run, slug: str) -> dict[str, bool] | None:
    """Which settings are already on; None when GitHub would not say."""
    code, output = run(["gh", "api", f"repos/{slug}", "--jq", ".delete_branch_on_merge"])
    if code != 0:
        return None
    state = {DELETE_BRANCH: output.strip() == "true"}
    code, output = run(["gh", "api", f"repos/{slug}/actions/permissions/workflow", "--jq",
                        '"\\(.default_workflow_permissions) \\(.can_approve_pull_request_reviews)"'])
    if code != 0:
        return None
    state[ACTIONS_WRITE] = output.strip() == "write true"
    return state


def missing(state: dict[str, bool], root: Path) -> list[str]:
    """Settings this project should have and does not."""
    wanted = [DELETE_BRANCH] + ([ACTIONS_WRITE] if has_release_automation(root) else [])
    return [key for key in wanted if not state.get(key)]


def apply(run, slug: str, keys: list[str]) -> list[str]:
    """Apply the settings; returns the ones GitHub refused."""
    calls = commands(slug)
    return [key for key in keys if run(calls[key])[0] != 0]


def step(root: Path, run, confirm, has_origin: bool) -> tuple[str, str]:
    """The guided-start step: say what is missing, ask once, apply through gh.

    When GitHub refuses (organisation limits, no owner rights) the commands are shown for manual
    use and the start goes on — a missing setting must not block the remaining steps.
    """
    manual = "ustaw ręcznie: docs/SETUP.md, krok 1"
    if not has_origin:
        return SKIPPED, "pominięte — nie ma podpiętego repo"
    slug, why_not = repo_slug(run)
    if not slug:
        return SKIPPED, f"pominięte — {why_not}"
    state = read_state(run, slug)
    if state is None:
        return SKIPPED, f"nie udało się odczytać ustawień repo (potrzebne uprawnienia właściciela) — {manual}"
    todo = missing(state, root)
    if not todo:
        return DONE, "ustawienia repo są na miejscu"
    for key in todo:
        print(f"  {mark(PENDING)} {LABELS[key]} {paint('— ' + WHY[key], DIM)}")
    if not confirm("Ustawić to w repo na GitHubie?"):
        return SKIPPED, f"pominięte — {manual}"
    refused = apply(run, slug, todo)
    if refused:
        notice("GitHub odmówił (ograniczenia organizacji albo brak uprawnień właściciela). Ręcznie:")
        for key in refused:
            print(f"    {' '.join(commands(slug)[key])}")
        return SKIPPED, "nie ustawione: " + "; ".join(LABELS[key] for key in refused)
    return DONE, "ustawione: " + "; ".join(LABELS[key] for key in todo)


def doctor_check(root: Path, run, ok, warn) -> None:
    """The doctor's view of the same settings — silent when there is no GitHub repo to ask."""
    slug, _ = repo_slug(run)
    state = read_state(run, slug) if slug else None
    if state is None:
        return
    todo = missing(state, root)
    if not todo:
        ok(f"GitHub repo settings in place ({slug})")
        return
    warn("GitHub repo settings missing: " + "; ".join(LABELS[key] for key in todo),
         "Set them with: python3 scripts/project-setup.py  (or by hand — docs/SETUP.md step 1)")
