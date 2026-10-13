"""Tests for scripts/project-setup.py — the guided steps after new-project.py.

The steps used to be a printed list the user had to retype. Now each one asks, runs and reports;
a done step is skipped on a second run, and a failed one offers the AI's help with the exact
command and error. Without a terminal nothing is asked and nothing is run.

The module talks to the outside only through is_tty / ask / run / start_claude, so the tests
replace those; two cases use a real git repository.
"""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "project-setup.py"


def _load():
    spec = importlib.util.spec_from_file_location("project_setup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Fake:
    """Scripted answers and command results; records what was asked, run and handed to claude."""

    def __init__(self, mod, answers=(), results=None, tty=True, claude=True, in_claude=None):
        """claude=False: claude is not installed. in_claude: callables run one per Claude Code
        session, standing in for what the user and the AI did there (write the brief, fix a tool)."""
        self.answers = list(answers)
        self.results = results or {}
        self.asked, self.ran, self.claude = [], [], []
        self.claude_installed = claude
        self.in_claude = list(in_claude or [])
        self.interactive, self.interactive_code = [], 0
        mod.is_tty = lambda: tty
        mod.ask = self._ask
        mod.run = self._run
        mod.run_interactive = self._run_interactive
        mod.start_claude = self._start_claude

    def _run_interactive(self, command):
        self.interactive.append(" ".join(command))
        return self.interactive_code

    def _start_claude(self, prompt):
        if not self.claude_installed:
            return False
        self.claude.append(prompt)
        if self.in_claude:
            self.in_claude.pop(0)()
        return True

    def _ask(self, prompt):
        self.asked.append(prompt)
        assert self.answers, f"unexpected question: {prompt}"
        return self.answers.pop(0)

    def _run(self, command, show=False):
        self.ran.append(command)
        for prefix, result in self.results.items():
            if " ".join(command).startswith(prefix):
                return result
        return 0, ""

    def commands(self):
        return [" ".join(c) for c in self.ran]


@pytest.fixture()
def mod(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


def _git_dir(root: Path) -> None:
    (root / ".git").mkdir()


# ── brief state ──────────────────────────────────────────────────────────────

def _write_scope(root: Path, text: str) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "PROJECT_SCOPE.md").write_text(text, encoding="utf-8")


def test_should_treat_missing_file_as_no_brief(mod):
    assert mod.scope_is_filled() is False


def test_should_treat_the_real_template_skeleton_as_no_brief(mod, tmp_path):
    # pins SCOPE_SCAFFOLD_MARKER to the skeleton the template actually ships
    _write_scope(tmp_path, (ROOT / "docs" / "PROJECT_SCOPE.md").read_text(encoding="utf-8"))
    assert mod.scope_is_filled() is False


def test_should_treat_own_content_as_a_brief(mod, tmp_path):
    _write_scope(tmp_path, "# Project Scope\n\nSklep z kawą.\n")
    assert mod.scope_is_filled() is True


def test_should_describe_the_same_marker_in_the_scope_skill(mod):
    skill = (ROOT / ".claude" / "skills" / "new-project-scope" / "SKILL.md").read_text(encoding="utf-8")
    assert mod.SCOPE_SCAFFOLD_MARKER in skill


# ── step: git repository ─────────────────────────────────────────────────────

def test_should_skip_git_step_when_repository_exists(mod, tmp_path):
    _git_dir(tmp_path)
    fake = Fake(mod)
    assert mod.step_git()[0] == mod.DONE
    assert fake.asked == [] and fake.ran == []


def test_should_create_repository_on_main_when_user_agrees(mod):
    fake = Fake(mod, answers=[""])
    assert mod.step_git()[0] == mod.DONE
    assert fake.commands() == ["git init -q -b main"]


def test_should_really_create_repository_on_main(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(module, "ask", lambda prompt: "")
    assert module.step_git()[0] == module.DONE
    head = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=tmp_path,
                          capture_output=True, text=True).stdout.strip()
    assert head == "main"


# ── step: remote / GitHub repository ─────────────────────────────────────────

def test_should_skip_remote_step_when_origin_is_set(mod, tmp_path):
    _git_dir(tmp_path)
    fake = Fake(mod, results={"git remote get-url origin": (0, "git@github.com:acme/shop.git\n")})
    mark, message = mod.step_remote()
    assert mark == mod.DONE and "acme/shop" in message
    assert fake.asked == []


def test_should_add_existing_repository_address_as_origin(mod, tmp_path):
    _git_dir(tmp_path)
    fake = Fake(mod, answers=["git@github.com:acme/shop.git"],
                results={"git remote get-url origin": (2, "")})
    assert mod.step_remote()[0] == mod.DONE
    assert "git remote add origin git@github.com:acme/shop.git" in fake.commands()
    assert not any(c.startswith("gh ") for c in fake.commands())


@pytest.mark.parametrize("answer, flag", [("", "--private"), ("n", "--public")])
def test_should_create_github_repository_from_owner_and_name(mod, tmp_path, answer, flag):
    _git_dir(tmp_path)
    fake = Fake(mod, answers=["acme/shop", answer], results={"git remote get-url origin": (2, "")})
    assert mod.step_remote()[0] == mod.DONE
    assert f"gh repo create acme/shop {flag} --source . --remote origin" in fake.commands()


def test_should_never_push_when_creating_the_repository(mod, tmp_path):
    _git_dir(tmp_path)
    fake = Fake(mod, answers=["acme/shop", ""], results={"git remote get-url origin": (2, "")})
    mod.step_remote()
    assert not any("push" in c for c in fake.commands())


def test_should_skip_remote_step_on_empty_answer(mod, tmp_path):
    _git_dir(tmp_path)
    fake = Fake(mod, answers=[""], results={"git remote get-url origin": (2, "")})
    assert mod.step_remote()[0] == mod.SKIPPED
    assert fake.commands() == ["git remote get-url origin"]


def test_should_ask_again_when_answer_is_neither_address_nor_owner_name(mod, tmp_path):
    _git_dir(tmp_path)
    fake = Fake(mod, answers=["moj projekt", ""], results={"git remote get-url origin": (2, "")})
    assert mod.step_remote()[0] == mod.SKIPPED
    assert len(fake.asked) == 2


@pytest.mark.parametrize("answer, kind", [
    ("git@github.com:acme/shop.git", "url"), ("https://github.com/acme/shop", "url"),
    ("../other.git", "url"), ("acme/shop", "slug"), ("acme/shop.pl", "slug"),
    ("shop", ""), ("a/b/c", ""), ("moj projekt", ""),
])
def test_should_classify_repository_answer(mod, answer, kind):
    assert mod.classify_repo_answer(answer) == kind


def test_should_fail_the_step_when_gh_is_missing(mod, tmp_path):
    _git_dir(tmp_path)
    Fake(mod, answers=["acme/shop", ""],
         results={"git remote get-url origin": (2, ""), "gh repo create": (127, "nie znaleziono polecenia: gh")})
    with pytest.raises(mod.StepFailed) as failure:
        mod.step_remote()
    assert failure.value.code == 127


# ── step: labels ─────────────────────────────────────────────────────────────

GITHUB = {"git remote get-url origin": (0, "git@github.com:acme/shop.git\n"),
          "gh repo view": (0, "acme/shop\n"),
          # repository settings already in place (longer prefix first: both start with gh api repos/acme/shop)
          "gh api repos/acme/shop/actions/permissions/workflow": (0, "write true\n"),
          "gh api repos/acme/shop": (0, "true\n")}


def test_should_skip_labels_when_no_github_repository_is_connected(mod):
    fake = Fake(mod, results={"git remote get-url origin": (2, "")})
    assert mod.step_labels()[0] == mod.SKIPPED
    assert not any(c.startswith("gh ") for c in fake.commands())


def test_should_skip_labels_when_origin_is_not_github(mod):
    fake = Fake(mod, results={"git remote get-url origin": (0, "git@gitlab.com:acme/shop.git\n"),
                              "gh repo view": (1, "none of the git remotes point to a known GitHub host")})
    mark, message = mod.step_labels()
    assert mark == mod.SKIPPED and "nie jest na GitHubie" in message
    assert not any(c.startswith("gh label") for c in fake.commands())


def test_should_skip_labels_with_a_clear_reason_when_gh_is_not_installed(mod):
    fake = Fake(mod, results={"git remote get-url origin": (0, "git@github.com:acme/shop.git\n"),
                              "gh repo view": (127, "nie znaleziono polecenia: gh")})
    mark, message = mod.step_labels()
    assert mark == mod.SKIPPED and "gh" in message
    assert not any(c.startswith("gh label") for c in fake.commands())


def test_should_create_labels_when_origin_uses_an_ssh_host_alias(mod):
    # found live: `gh repo create` added git@github-work:owner/name.git (SSH alias), the old check
    # looked for "github.com" in the address and skipped the labels right after creating the repo
    fake = Fake(mod, answers=[""], results={
        "git remote get-url origin": (0, "git@github-work:acme/shop.git\n"),
        "gh repo view": (0, "acme/shop\n"), "gh label list": (0, ""),
    })
    assert mod.step_labels()[0] == mod.DONE
    assert len([c for c in fake.commands() if c.startswith("gh label create")]) == 2


def test_should_create_only_missing_labels(mod):
    fake = Fake(mod, answers=[""], results={**GITHUB, "gh label list": (0, "bug\nowner\n")})
    assert mod.step_labels()[0] == mod.DONE
    created = [c for c in fake.commands() if c.startswith("gh label create")]
    assert len(created) == 1 and created[0].startswith("gh label create idea ")


def test_should_not_ask_when_labels_exist(mod):
    fake = Fake(mod, results={**GITHUB, "gh label list": (0, "owner\nidea\n")})
    assert mod.step_labels()[0] == mod.DONE
    assert fake.asked == []


def test_should_create_no_labels_when_user_declines(mod):
    fake = Fake(mod, answers=["n"], results={**GITHUB, "gh label list": (0, "")})
    assert mod.step_labels()[0] == mod.SKIPPED
    assert not any(c.startswith("gh label create") for c in fake.commands())


# ── steps: skills, doctor ────────────────────────────────────────────────────

def _script(root: Path, name: str) -> None:
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts" / name).write_text("# stub")


def test_should_install_skills_when_user_agrees(mod, tmp_path):
    _script(tmp_path, "update-skills.py")
    fake = Fake(mod, answers=[""])
    assert mod.step_skills()[0] == mod.DONE
    assert fake.commands()[0].endswith("scripts/update-skills.py --apply")


def test_should_not_refresh_skills_when_user_declines(mod, tmp_path):
    _script(tmp_path, "update-skills.py")
    fake = Fake(mod, answers=["n"])
    mark, message = mod.step_skills()
    assert mark == mod.DONE and "update-skills.py --apply" in message
    assert fake.ran == []


def test_should_let_the_user_choose_skill_groups_before_refreshing(mod, tmp_path):
    _script(tmp_path, "select-skills.py")
    _script(tmp_path, "update-skills.py")
    fake = Fake(mod, answers=[""])
    assert mod.step_skills()[0] == mod.DONE
    assert len(fake.interactive) == 1 and fake.interactive[0].endswith("scripts/select-skills.py")
    assert fake.commands()[0].endswith("scripts/update-skills.py --apply")  # after the choice


def test_should_fail_the_step_when_the_skill_chooser_fails(mod, tmp_path):
    _script(tmp_path, "select-skills.py")
    fake = Fake(mod)
    fake.interactive_code = 1
    with pytest.raises(mod.StepFailed):
        mod.step_skills()


def test_should_skip_skills_step_when_the_project_has_no_skill_scripts(mod):
    Fake(mod)
    assert mod.step_skills()[0] == mod.SKIPPED


def test_should_fail_doctor_step_on_red_report(mod, tmp_path):
    _script(tmp_path, "doctor.py")
    Fake(mod, results={"": (1, "1 required check(s) failed")})
    with pytest.raises(mod.StepFailed) as failure:
        mod.step_doctor()
    assert "required check" in failure.value.output


def test_should_pass_doctor_step_on_green_report(mod, tmp_path):
    _script(tmp_path, "doctor.py")
    Fake(mod)
    assert mod.step_doctor()[0] == mod.DONE


# ── step: brief ──────────────────────────────────────────────────────────────

BRIEF = "# Project Scope\n\nSklep z kawą.\n"


def _write_config(root: Path, data: dict) -> None:
    path = root / ".claude" / "hooks" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_adr(root: Path, name: str = "ADR-001-stack.md") -> None:
    (root / "docs" / "adr").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "adr" / name).write_text("# ADR-001\n", encoding="utf-8")


def _complete_interview(root: Path):
    """What a finished scope interview leaves behind."""
    def session():
        _write_scope(root, BRIEF)
        _write_config(root, {"stack": "laravel", "src_dirs": ["app"]})
        _write_adr(root)
    return session


def _complete_design(root: Path):
    """What a finished design stage leaves behind."""
    def session():
        (root / "mockups" / "propozycje").mkdir(parents=True, exist_ok=True)
        (root / "mockups" / "propozycje" / "kierunek-1-jasna.html").write_text("<html></html>", encoding="utf-8")
        (root / "docs").mkdir(exist_ok=True)
        (root / "docs" / "UI_GUIDELINES.md").write_text("# UI\n\n## Kierunek wizualny projektu\n\nTokeny.\n",
                                                        encoding="utf-8")
    return session


def test_should_report_brief_done_when_interview_left_brief_stack_and_adr(mod, tmp_path, capsys):
    fake = Fake(mod, answers=[""], in_claude=[_complete_interview(tmp_path)])
    mark, _ = mod.step_brief()
    assert mark == mod.DONE
    assert fake.claude == ["scope"]
    out = capsys.readouterr().out
    assert out.count(mod.DONE) == 3 and "laravel" in out


def test_should_show_what_is_missing_and_offer_to_return_when_interview_was_left_early(mod, tmp_path, capsys):
    # the user left Claude Code after the brief was written, before the stack was set
    fake = Fake(mod, answers=["", "n"], in_claude=[lambda: _write_scope(tmp_path, BRIEF)])
    mark, message = mod.step_brief()
    assert mark == mod.SKIPPED
    assert "brakuje" in message and "stos" in message and "ADR-001" in message
    assert "Wrócić do Claude Code" in fake.asked[-1]
    out = capsys.readouterr().out
    assert out.count(mod.DONE) == 1 and out.count(mod.FAILED) == 2


def test_should_reopen_claude_and_finish_when_user_returns_to_the_interview(mod, tmp_path):
    fake = Fake(mod, answers=["", ""], in_claude=[
        lambda: _write_scope(tmp_path, BRIEF),
        _complete_interview(tmp_path),
    ])
    assert mod.step_brief()[0] == mod.DONE
    assert fake.claude == ["scope", "scope"]


def test_should_not_count_nothing_written_as_a_brief(mod, tmp_path):
    fake = Fake(mod, answers=["", "n"], in_claude=[lambda: None])
    mark, message = mod.step_brief()
    assert mark == mod.SKIPPED and "brief" in message
    assert fake.claude == ["scope"]


def test_should_not_count_the_template_example_as_adr_001(mod, tmp_path):
    _write_scope(tmp_path, BRIEF)
    _write_config(tmp_path, {"stack": "node"})
    _write_adr(tmp_path, "ADR-001-example.md")
    assert [ok for ok, _ in mod.brief_checks()] == [True, True, False]


def test_should_not_count_default_directories_as_a_set_stack(mod, tmp_path):
    _write_scope(tmp_path, BRIEF)
    _write_config(tmp_path, {"src_dirs": ["src"]})
    _write_adr(tmp_path)
    assert [ok for ok, _ in mod.brief_checks()] == [True, False, True]


def test_should_leave_instruction_when_user_declines_brief(mod):
    fake = Fake(mod, answers=["n"])
    mark, message = mod.step_brief()
    assert mark == mod.SKIPPED and "scope" in message
    assert fake.claude == []


def test_should_leave_instruction_when_claude_is_not_installed(mod):
    Fake(mod, answers=[""], claude=False)
    mark, message = mod.step_brief()
    assert mark == mod.SKIPPED and "scope" in message


def test_should_skip_interview_without_asking_when_everything_is_there(mod, tmp_path):
    _complete_interview(tmp_path)()
    fake = Fake(mod)
    mark, message = mod.step_brief()
    assert mark == mod.DONE and "pominięty" in message
    assert fake.asked == [] and fake.claude == []


def test_should_offer_to_finish_when_brief_exists_but_stack_is_not_set(mod, tmp_path):
    _write_scope(tmp_path, BRIEF)
    fake = Fake(mod, answers=["n"])
    mark, _ = mod.step_brief()
    assert mark == mod.SKIPPED
    assert "dokończyć" in fake.asked[0]


# ── start_claude: a child process, so the user comes back ────────────────────

def test_should_run_claude_as_a_child_process_and_return(tmp_path, monkeypatch, capsys):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/claude")
    calls = []
    monkeypatch.setattr(module.subprocess, "call", lambda command, cwd: calls.append((command, cwd)) or 0)
    assert module.start_claude("scope") is True
    assert calls == [(["claude", "scope"], str(tmp_path))]
    out = capsys.readouterr().out
    assert "wrócisz do kroków startu" in out and "Z powrotem w krokach startu" in out


def test_should_not_replace_its_own_process_with_claude():
    # os.execvp was the reason leaving Claude Code lost the remaining steps
    source = SCRIPT.read_text(encoding="utf-8")
    assert "os.exec" not in source.replace("os.execvp was", "")


def test_should_restore_ctrl_c_handling_after_claude_exits(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/claude")
    during = []
    monkeypatch.setattr(module.subprocess, "call",
                        lambda command, cwd: during.append(module.signal.getsignal(module.signal.SIGINT)) or 0)
    before = module.signal.getsignal(module.signal.SIGINT)
    module.start_claude("scope")
    assert during == [module.signal.SIG_IGN]
    assert module.signal.getsignal(module.signal.SIGINT) == before


def test_should_say_how_to_start_the_wizard_when_claude_is_missing(tmp_path, monkeypatch, capsys):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    assert module.start_claude("scope") is False
    assert "scope" in capsys.readouterr().out


# ── whole flow ───────────────────────────────────────────────────────────────

def test_should_only_print_steps_without_a_terminal(mod, capsys):
    fake = Fake(mod, tty=False)
    assert mod.main([]) == 0
    out = capsys.readouterr().out
    assert fake.asked == [] and fake.ran == [] and fake.claude == []
    for title, _, _, _ in mod.STEPS:
        assert title in out


def test_should_only_print_steps_with_list_flag(mod, capsys):
    fake = Fake(mod)
    assert mod.main(["--list"]) == 0
    assert fake.asked == [] and fake.ran == []


def test_should_order_brief_then_skills_then_design(mod):
    # the brief feeds both later steps (stack -> skill groups, content -> mockups); skills are
    # chosen before the design stage so it already runs without the unneeded ones
    order = [step for _, _, _, step in mod.STEPS]
    assert order.index(mod.step_brief) < order.index(mod.step_skills) < order.index(mod.step_design)
    assert order[-1] is mod.step_design


def test_should_say_so_when_the_design_skill_group_was_not_kept(mod, tmp_path, capsys):
    Fake(mod, answers=["", "n"])
    mod.step_design()
    assert "Projektowanie wyglądu" in capsys.readouterr().out
    (tmp_path / ".claude" / "skills" / "design-taste-frontend").mkdir(parents=True)
    Fake(mod, answers=["", "n"])
    mod.step_design()
    assert "Projektowanie wyglądu” nie jest" not in capsys.readouterr().out


# ── step: design ─────────────────────────────────────────────────────────────

def test_should_hand_the_design_task_to_claude_and_report_done(mod, tmp_path, capsys):
    fake = Fake(mod, answers=["", ""], in_claude=[_complete_design(tmp_path)])  # impeccable: no, design: yes
    mark, _ = mod.step_design()
    assert mark == mod.DONE
    prompt = fake.claude[0]
    assert "docs/PROJECT_SCOPE.md" in prompt and "mockups/propozycje/" in prompt
    assert "design-taste-frontend" in prompt and "ui-ux-pro-max" in prompt
    assert "impeccable" not in prompt  # not installed here, so the task does not mention it
    assert "## Kierunek wizualny projektu" in prompt and "/exit" in prompt
    assert capsys.readouterr().out.count(mod.DONE) == 2


def test_should_skip_design_when_the_project_has_no_interface(mod):
    fake = Fake(mod, answers=["", "n"])
    mark, message = mod.step_design()
    assert mark == mod.SKIPPED and "szablon graficzny" in message
    assert fake.claude == []


def test_should_show_missing_guidelines_when_only_mockups_were_made(mod, tmp_path, capsys):
    def only_mockups():
        (tmp_path / "mockups" / "propozycje").mkdir(parents=True)
        (tmp_path / "mockups" / "propozycje" / "index.html").write_text("<html></html>", encoding="utf-8")

    fake = Fake(mod, answers=["", "", "n"], in_claude=[only_mockups])
    mark, message = mod.step_design()
    assert mark == mod.SKIPPED and "UI_GUIDELINES" in message
    out = capsys.readouterr().out
    assert out.count(mod.DONE) == 1 and out.count(mod.FAILED) == 1


def test_should_not_count_the_template_guidelines_as_a_visual_direction(mod, tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "UI_GUIDELINES.md").write_text((ROOT / "docs" / "UI_GUIDELINES.md").read_text(encoding="utf-8"),
                                                        encoding="utf-8")
    assert [ok for ok, _ in mod.design_checks()] == [False, False]


def test_should_skip_design_without_asking_when_it_is_already_there(mod, tmp_path):
    _complete_design(tmp_path)()
    fake = Fake(mod)
    assert mod.step_design()[0] == mod.DONE
    assert fake.asked == [] and fake.claude == []


def test_should_not_install_impeccable_unless_the_user_says_yes(mod, capsys):
    # Enter means NO here, unlike the other questions: its bundled scripts did not pass the
    # template's security scan, so it enters a project only on an explicit decision
    fake = Fake(mod, answers=["", "n"])
    mod.step_design()
    assert fake.interactive == []
    assert "[t/N]" in fake.asked[0] and "impeccable" in fake.asked[0]


def test_should_install_impeccable_into_the_project_on_explicit_yes(mod):
    fake = Fake(mod, answers=["t", "n"])
    mod.step_design()
    assert fake.interactive == ["npx impeccable install --providers=claude --scope=project --no-hooks"]


def test_should_make_impeccable_lead_the_design_when_it_is_installed(mod, tmp_path):
    # found live: with "use it if present" Claude designed without it and reached for impeccable
    # only when the user asked; it also had no PRODUCT.md and no word on where mockups go
    (tmp_path / ".claude" / "skills" / "impeccable").mkdir(parents=True)
    fake = Fake(mod, answers=[""], in_claude=[_complete_design(tmp_path)])
    mod.step_design()
    prompt = fake.claude[0]
    assert "prowadź pracę NIM, od początku" in prompt
    assert "PRODUCT.md" in prompt and "docs/PROJECT_SCOPE.md" in prompt
    assert "critique" in prompt
    assert prompt.count("mockups/propozycje/") >= 2  # where the mockups go, also for impeccable


def test_should_use_the_freshly_installed_impeccable_in_the_same_step(mod, tmp_path):
    def installed(command):
        (tmp_path / ".claude" / "skills" / "impeccable").mkdir(parents=True)
        return 0

    fake = Fake(mod, answers=["t", ""], in_claude=[_complete_design(tmp_path)])
    mod.run_interactive = installed
    mod.step_design()
    assert "prowadź pracę NIM" in fake.claude[0]


def test_should_keep_installer_away_from_the_hook_settings(mod):
    # .claude/settings.local.json holds the guard hooks; the installer must not rewrite it
    assert "--no-hooks" in mod.IMPECCABLE_INSTALL and "--scope=project" in mod.IMPECCABLE_INSTALL


def test_should_go_on_without_impeccable_when_its_installation_fails(mod, tmp_path, capsys):
    fake = Fake(mod, answers=["t", ""], in_claude=[_complete_design(tmp_path)])
    fake.interactive_code = 1
    assert mod.step_design()[0] == mod.DONE
    assert "nie powiodła się" in capsys.readouterr().out


def test_should_not_ask_about_impeccable_when_it_is_already_installed(mod, tmp_path):
    (tmp_path / ".claude" / "skills" / "impeccable").mkdir(parents=True)
    fake = Fake(mod, answers=["n"])
    mod.step_design()
    assert len(fake.asked) == 1 and "impeccable" not in fake.asked[0]


@pytest.mark.parametrize("answer, default, expected", [
    ("", True, True), ("", False, False), ("t", False, True), ("n", True, False), ("tak", False, True), ("x", True, False),
])
def test_should_treat_enter_as_the_default_answer(mod, answer, default, expected):
    Fake(mod, answers=[answer])
    assert mod.confirm("Pytanie?", default=default) is expected


def test_should_walk_through_every_step_in_order_and_end_with_a_summary(mod, tmp_path, capsys):
    _git_dir(tmp_path)
    _script(tmp_path, "update-skills.py")
    _script(tmp_path, "doctor.py")
    _complete_interview(tmp_path)()
    _complete_design(tmp_path)()
    Fake(mod, answers=[""], results={**GITHUB, "gh label list": (0, "owner\nidea\n")})
    assert mod.main([]) == 0
    out = capsys.readouterr().out
    headers = [line for line in out.splitlines() if "Krok " in line and "/" in line]
    assert len(headers) == len(mod.STEPS)
    for number, ((title, _, why, _), header) in enumerate(zip(mod.STEPS, headers), start=1):
        assert f"Krok {number}/{len(mod.STEPS)}" in header and title in header
        assert why in out  # every step says what it is for
    summary = out[out.index("Podsumowanie"):]
    for title, _, _, _ in mod.STEPS:
        assert title in summary
    assert "Start projektu zakończony" in summary
    assert "pierwszym commitem" in summary
    assert "Co dalej" in summary


DOCTOR_RED = (1, "✗ pre-commit not available\n1 required check(s) failed")


def _failing_doctor(mod, tmp_path, answers, in_claude=None):
    _git_dir(tmp_path)
    _script(tmp_path, "doctor.py")
    fake = Fake(mod, answers=answers, in_claude=in_claude, results={
        **GITHUB, "gh label list": (0, "owner\nidea\n"),
        f"{mod.sys.executable} scripts/doctor.py": DOCTOR_RED,
    })
    return fake


def test_should_offer_ai_help_with_command_and_error_when_a_step_fails(mod, tmp_path, capsys):
    fake = _failing_doctor(mod, tmp_path, answers=["", "n"])  # help: yes, retry: no
    assert mod.main([]) == 1
    assert len(fake.claude) == 1
    prompt = fake.claude[0]
    assert "Kontrola środowiska" in prompt
    assert "scripts/doctor.py" in prompt
    assert "Kod wyjścia: 1" in prompt
    assert "pre-commit not available" in prompt
    assert "python3 scripts/project-setup.py" in prompt
    assert "Krok 6/8" not in capsys.readouterr().out  # later steps wait for the fix


def test_should_run_the_step_again_and_continue_after_ai_help(mod, tmp_path, capsys):
    _complete_interview(tmp_path)()
    _complete_design(tmp_path)()

    def fixed_in_claude():
        fake.results[f"{mod.sys.executable} scripts/doctor.py"] = (0, "All required checks passed.")

    fake = _failing_doctor(mod, tmp_path, answers=["", ""], in_claude=[fixed_in_claude])  # help: yes, retry: yes
    assert mod.main([]) == 0
    doctor_runs = [c for c in fake.commands() if c.endswith("scripts/doctor.py")]
    assert len(doctor_runs) == 2
    out = capsys.readouterr().out
    assert "Krok 6/8" in out and "Krok 8/8" in out and "Start projektu zakończony" in out


def test_should_ask_about_retry_also_when_user_declines_ai_help(mod, tmp_path):
    fake = _failing_doctor(mod, tmp_path, answers=["n", "n"])
    assert mod.main([]) == 1
    assert fake.claude == []
    assert "Ponowić ten krok" in fake.asked[-1]


def test_should_summarise_failed_and_pending_steps_with_the_resume_command(mod, tmp_path, capsys):
    _failing_doctor(mod, tmp_path, answers=["n", "n"])
    assert mod.main([]) == 1
    summary = capsys.readouterr().out.split("Podsumowanie")[1]
    assert f"{mod.FAILED} Kontrola środowiska" in summary
    assert f"{mod.PENDING} Brief projektu" in summary
    assert "python3 scripts/project-setup.py" in summary
    assert "Start projektu zakończony" not in summary
    assert "Start niedokończony" in summary


def test_should_stop_cleanly_when_user_interrupts(mod, tmp_path, capsys):
    def interrupted(prompt):
        raise KeyboardInterrupt
    Fake(mod)
    mod.ask = interrupted
    assert mod.main([]) == 130
    assert "python3 scripts/project-setup.py" in capsys.readouterr().out


# ── look: colours on a terminal, plain text everywhere else ──────────────────

def test_should_print_plain_text_when_output_is_not_a_terminal(mod, tmp_path, capsys):
    _complete_interview(tmp_path)()
    _complete_design(tmp_path)()
    _git_dir(tmp_path)
    Fake(mod, answers=[""], results={**GITHUB, "gh label list": (0, "owner\nidea\n")})
    mod.main([])
    assert "\033[" not in capsys.readouterr().out


# ── step: repository settings (docs/SETUP.md step 1) ─────────────────────────

SETTINGS_OFF = {"git remote get-url origin": (0, "git@github-work:acme/shop.git\n"),
                "gh repo view": (0, "acme/shop\n"),
                "gh api repos/acme/shop/actions/permissions/workflow": (0, "read false\n"),
                "gh api repos/acme/shop": (0, "false\n")}


def _release_workflow(root: Path) -> None:
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "release-please.yml").write_text("name: release\n", encoding="utf-8")


def test_should_put_repo_settings_right_after_the_repository_step(mod):
    order = [step for _, _, _, step in mod.STEPS]
    assert order.index(mod.step_repo_settings) == order.index(mod.step_remote) + 1


def test_should_apply_both_settings_after_one_question_when_project_has_release_automation(mod, tmp_path, capsys):
    _release_workflow(tmp_path)
    fake = Fake(mod, answers=[""], results=SETTINGS_OFF)
    mark, message = mod.step_repo_settings()
    assert mark == mod.DONE
    assert len(fake.asked) == 1
    applied = [c for c in fake.commands() if " -X " in c]
    assert applied == [
        "gh api -X PATCH repos/acme/shop -F delete_branch_on_merge=true",
        "gh api -X PUT repos/acme/shop/actions/permissions/workflow -f default_workflow_permissions=write "
        "-F can_approve_pull_request_reviews=true",
    ]
    out = capsys.readouterr().out
    assert "automat wydań" in out  # says what the broader permission is for before asking


def test_should_not_propose_actions_permissions_when_project_has_no_release_automation(mod, tmp_path, capsys):
    fake = Fake(mod, answers=[""], results=SETTINGS_OFF)
    assert mod.step_repo_settings()[0] == mod.DONE
    applied = [c for c in fake.commands() if " -X " in c]
    assert applied == ["gh api -X PATCH repos/acme/shop -F delete_branch_on_merge=true"]
    assert "uprawnienia automatów" not in capsys.readouterr().out


def test_should_change_nothing_when_user_declines_repo_settings(mod, tmp_path):
    _release_workflow(tmp_path)
    fake = Fake(mod, answers=["n"], results=SETTINGS_OFF)
    mark, message = mod.step_repo_settings()
    assert mark == mod.SKIPPED and "krok 1" in message
    assert not any(" -X " in c for c in fake.commands())


def test_should_skip_repo_settings_without_asking_when_they_are_in_place(mod, tmp_path):
    _release_workflow(tmp_path)
    fake = Fake(mod, results=GITHUB)
    assert mod.step_repo_settings()[0] == mod.DONE
    assert fake.asked == [] and not any(" -X " in c for c in fake.commands())


def test_should_show_manual_commands_and_go_on_when_github_refuses(mod, tmp_path, capsys):
    _release_workflow(tmp_path)
    Fake(mod, answers=[""], results={**SETTINGS_OFF, "gh api -X PUT": (1, "HTTP 403")})
    mark, message = mod.step_repo_settings()  # no StepFailed: the start must not stop here
    assert mark == mod.SKIPPED and "uprawnienia automatów" in message and "kasowanie" not in message
    out = capsys.readouterr().out
    assert "gh api -X PUT repos/acme/shop/actions/permissions/workflow" in out


@pytest.mark.parametrize("results, reason", [
    ({"git remote get-url origin": (2, "")}, "nie ma podpiętego repo"),
    ({"git remote get-url origin": (0, "git@gitlab.com:a/b.git\n"), "gh repo view": (1, "no known host")}, "nie jest na GitHubie"),
    ({"git remote get-url origin": (0, "git@github.com:a/b.git\n"), "gh repo view": (127, "")}, "gh"),
    ({"git remote get-url origin": (0, "git@github.com:a/b.git\n"), "gh repo view": (0, "a/b\n"),
      "gh api repos/a/b": (1, "HTTP 404")}, "nie udało się odczytać"),
])
def test_should_skip_repo_settings_with_a_reason_when_they_cannot_be_read(mod, results, reason):
    fake = Fake(mod, results=results)
    mark, message = mod.step_repo_settings()
    assert mark == mod.SKIPPED and reason in message
    assert fake.asked == [] and not any(" -X " in c for c in fake.commands())
