"""Tests for scripts/project-setup.py — the guided steps after new-project.py.

The steps used to be a printed list the user had to retype. Now each one asks, runs and reports;
a done step is skipped on a second run, and a failed one offers the AI's help with the exact
command and error. Without a terminal nothing is asked and nothing is run.

The module talks to the outside only through is_tty / ask / run / start_claude, so the tests
replace those; two cases use a real git repository.
"""
import importlib.util
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

    def __init__(self, mod, answers=(), results=None, tty=True):
        self.answers = list(answers)
        self.results = results or {}
        self.asked, self.ran, self.claude = [], [], []
        mod.is_tty = lambda: tty
        mod.ask = self._ask
        mod.run = self._run
        mod.start_claude = self.claude.append

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

GITHUB = {"git remote get-url origin": (0, "git@github.com:acme/shop.git\n")}


def test_should_skip_labels_when_no_github_repository_is_connected(mod):
    fake = Fake(mod, results={"git remote get-url origin": (2, "")})
    assert mod.step_labels()[0] == mod.SKIPPED
    assert not any(c.startswith("gh ") for c in fake.commands())


def test_should_skip_labels_when_origin_is_not_github(mod):
    fake = Fake(mod, results={"git remote get-url origin": (0, "git@gitlab.com:acme/shop.git\n")})
    assert mod.step_labels()[0] == mod.SKIPPED
    assert not any(c.startswith("gh ") for c in fake.commands())


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


def test_should_not_install_skills_when_user_declines(mod, tmp_path):
    _script(tmp_path, "update-skills.py")
    fake = Fake(mod, answers=["n"])
    assert mod.step_skills()[0] == mod.SKIPPED
    assert fake.ran == []


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

def test_should_start_scope_wizard_when_user_agrees(mod):
    fake = Fake(mod, answers=[""])
    mod.step_brief()
    assert fake.claude == ["scope"]


def test_should_leave_instruction_when_user_declines_brief(mod):
    fake = Fake(mod, answers=["n"])
    mark, message = mod.step_brief()
    assert mark == mod.SKIPPED and "scope" in message
    assert fake.claude == []


def test_should_skip_interview_and_point_to_set_stack_when_brief_exists(mod, tmp_path):
    _write_scope(tmp_path, "# Project Scope\n\nSklep z kawą.\n")
    fake = Fake(mod)
    mark, message = mod.step_brief()
    assert mark == mod.DONE and "set-stack.py" in message
    assert fake.asked == [] and fake.claude == []


# ── whole flow ───────────────────────────────────────────────────────────────

def test_should_only_print_steps_without_a_terminal(mod, capsys):
    fake = Fake(mod, tty=False)
    assert mod.main([]) == 0
    out = capsys.readouterr().out
    assert fake.asked == [] and fake.ran == [] and fake.claude == []
    for title, _, _ in mod.STEPS:
        assert title in out


def test_should_only_print_steps_with_list_flag(mod, capsys):
    fake = Fake(mod)
    assert mod.main(["--list"]) == 0
    assert fake.asked == [] and fake.ran == []


def test_should_keep_brief_as_the_last_step(mod):
    # it hands the terminal over to Claude Code, so nothing can come after it
    assert mod.STEPS[-1][2] is mod.step_brief


def test_should_walk_through_every_step_in_order(mod, tmp_path, capsys):
    _git_dir(tmp_path)
    _script(tmp_path, "update-skills.py")
    _script(tmp_path, "doctor.py")
    _write_scope(tmp_path, "# Project Scope\n\nSklep z kawą.\n")
    Fake(mod, answers=[""], results={**GITHUB, "gh label list": (0, "owner\nidea\n")})
    assert mod.main([]) == 0
    out = capsys.readouterr().out
    assert [line for line in out.splitlines() if line.startswith("── Krok")] == [
        f"── Krok {n}/{len(mod.STEPS)}: {title}" for n, (title, _, _) in enumerate(mod.STEPS, start=1)
    ]
    assert "Start projektu zakończony" in out


def _failing_doctor(mod, tmp_path, answers):
    _git_dir(tmp_path)
    _script(tmp_path, "doctor.py")
    return Fake(mod, answers=answers, results={
        **GITHUB, "gh label list": (0, "owner\nidea\n"),
        f"{mod.sys.executable} scripts/doctor.py": (1, "✗ pre-commit not available\n1 required check(s) failed"),
    })


def test_should_offer_ai_help_with_command_and_error_when_a_step_fails(mod, tmp_path, capsys):
    fake = _failing_doctor(mod, tmp_path, answers=[""])
    assert mod.main([]) == 1
    assert len(fake.claude) == 1
    prompt = fake.claude[0]
    assert "Kontrola środowiska" in prompt
    assert "scripts/doctor.py" in prompt
    assert "Kod wyjścia: 1" in prompt
    assert "pre-commit not available" in prompt
    assert "python3 scripts/project-setup.py" in prompt
    assert "Brief projektu" not in capsys.readouterr().out  # later steps wait for the fix


def test_should_leave_resume_command_when_user_declines_ai_help(mod, tmp_path, capsys):
    fake = _failing_doctor(mod, tmp_path, answers=["n"])
    assert mod.main([]) == 1
    assert fake.claude == []
    assert "python3 scripts/project-setup.py" in capsys.readouterr().out


def test_should_stop_cleanly_when_user_interrupts(mod, tmp_path, capsys):
    def interrupted(prompt):
        raise KeyboardInterrupt
    Fake(mod)
    mod.ask = interrupted
    assert mod.main([]) == 130
    assert "python3 scripts/project-setup.py" in capsys.readouterr().out
