"""Tests for scripts/doctor.py — the checks behind `npm run doctor`.

Regression for a report that was green while half the guard system was dead: doctor looked at
the commit layer only (pre-commit), so a fresh clone with no Claude Code hook wired — or with
the per-machine file still holding the INTERPRETER placeholder — passed every check.

Each case builds a throwaway repo layout in tmp_path and points doctor at it.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "doctor.py"

GUARDS = ["guard-alpha.py", "guard-beta.py"]


def _load():
    spec = importlib.util.spec_from_file_location("doctor", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def doctor(tmp_path, monkeypatch):
    """doctor module pointed at a fake repo holding two guard hooks and one non-guard hook."""
    mod = _load()
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name in [*GUARDS, "session-context.py"]:
        (hooks / name).write_text("# hook\n", encoding="utf-8")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    return mod


def _settings(interpreter="python3", guards=GUARDS):
    commands = [
        {"type": "command", "command": f"{interpreter} ${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{name}"}
        for name in guards
    ]
    return {
        "_readme": "Set the correct interpreter instead of INTERPRETER.",
        "hooks": {"PreToolUse": [{"matcher": "Bash|PowerShell", "hooks": commands}]},
    }


def _write_local(root: Path, data) -> None:
    text = data if isinstance(data, str) else json.dumps(data)
    (root / ".claude" / "settings.local.json").write_text(text, encoding="utf-8")


# ── check_claude_hooks ───────────────────────────────────────────────────────

def test_should_pass_when_every_guard_hook_is_wired(doctor, tmp_path, capsys):
    _write_local(tmp_path, _settings())
    assert doctor.check_claude_hooks() is True
    out = capsys.readouterr().out
    assert "✓" in out and "2 guard hook(s)" in out
    assert "⚠" not in out and "✗" not in out


def test_should_warn_without_failing_when_settings_file_is_missing(doctor, capsys):
    assert doctor.check_claude_hooks() is True
    out = capsys.readouterr().out
    assert "⚠" in out and "settings.local.json missing" in out
    assert "cp .claude/settings.local.json.example .claude/settings.local.json" in out


def test_should_fail_when_interpreter_placeholder_is_left(doctor, tmp_path, capsys):
    _write_local(tmp_path, _settings(interpreter="INTERPRETER"))
    assert doctor.check_claude_hooks() is False
    out = capsys.readouterr().out
    assert "✗" in out and "INTERPRETER placeholder" in out
    assert "✓" not in out


def test_should_ignore_placeholder_word_outside_hook_commands(doctor, tmp_path):
    # _settings() mentions INTERPRETER in "_readme"; only commands decide.
    _write_local(tmp_path, _settings(interpreter="py"))
    assert doctor.check_claude_hooks() is True


def test_should_list_guard_when_present_in_repo_but_not_wired(doctor, tmp_path, capsys):
    _write_local(tmp_path, _settings(guards=["guard-alpha.py"]))
    assert doctor.check_claude_hooks() is True
    out = capsys.readouterr().out
    assert "⚠" in out and "guard-beta.py" in out
    assert "guard-alpha.py" not in out
    assert "session-context.py" not in out
    assert "✓" not in out


def test_should_count_guard_wired_in_shared_settings(doctor, tmp_path, capsys):
    _write_local(tmp_path, _settings(guards=["guard-alpha.py"]))
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps(_settings(guards=["guard-beta.py"])), encoding="utf-8"
    )
    assert doctor.check_claude_hooks() is True
    assert "⚠" not in capsys.readouterr().out


def test_should_fail_when_settings_file_is_not_valid_json(doctor, tmp_path, capsys):
    _write_local(tmp_path, "{ not json")
    assert doctor.check_claude_hooks() is False
    assert "unreadable" in capsys.readouterr().out


def test_should_report_placeholder_and_unwired_guard_together(doctor, tmp_path, capsys):
    _write_local(tmp_path, _settings(interpreter="INTERPRETER", guards=["guard-alpha.py"]))
    assert doctor.check_claude_hooks() is False
    out = capsys.readouterr().out
    assert "INTERPRETER placeholder" in out and "guard-beta.py" in out


# ── check_pytest ─────────────────────────────────────────────────────────────

def test_should_report_version_when_pytest_is_available(doctor, monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run", lambda cmd: (0, "pytest 8.0.0"))
    doctor.check_pytest()
    out = capsys.readouterr().out
    assert "✓" in out and "pytest 8.0.0" in out


def test_should_warn_with_repair_commands_when_pytest_is_missing(doctor, monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run", lambda cmd: (1, "No module named pytest"))
    doctor.check_pytest()
    out = capsys.readouterr().out
    assert "⚠" in out
    assert "pip install --user pytest" in out
    assert "sudo apt install python3-pytest" in out


# ── check_claude_template_path ───────────────────────────────────────────────

def _write_hook_config(root: Path, name: str, data) -> None:
    text = data if isinstance(data, str) else json.dumps(data)
    (root / ".claude" / "hooks" / name).write_text(text, encoding="utf-8")


@pytest.fixture()
def no_template_env(monkeypatch):
    monkeypatch.delenv("AI_TEMPLATE_PATH", raising=False)


def test_should_use_local_path_when_set_only_in_config_local(doctor, tmp_path, capsys, no_template_env):
    clone = tmp_path / "template-clone"
    clone.mkdir()
    _write_hook_config(tmp_path, "config.json", {"lint": "x"})
    _write_hook_config(tmp_path, "config.local.json", {"ai_template_path": str(clone)})
    doctor.check_claude_template_path()
    out = capsys.readouterr().out
    assert "✓" in out and str(clone) in out and "from config.local.json" in out


def test_should_prefer_local_path_when_both_files_set_it(doctor, tmp_path, capsys, no_template_env):
    clone = tmp_path / "template-clone"
    clone.mkdir()
    _write_hook_config(tmp_path, "config.json", {"ai_template_path": str(tmp_path / "missing")})
    _write_hook_config(tmp_path, "config.local.json", {"ai_template_path": str(clone)})
    doctor.check_claude_template_path()
    out = capsys.readouterr().out
    assert "✓" in out and "from config.local.json" in out and "⚠" not in out


def test_should_prefer_env_variable_over_both_files(doctor, tmp_path, capsys, monkeypatch):
    clone = tmp_path / "env-clone"
    clone.mkdir()
    _write_hook_config(tmp_path, "config.local.json", {"ai_template_path": str(tmp_path / "missing")})
    monkeypatch.setenv("AI_TEMPLATE_PATH", str(clone))
    doctor.check_claude_template_path()
    out = capsys.readouterr().out
    assert "✓" in out and str(clone) in out and "from $AI_TEMPLATE_PATH" in out


def test_should_accept_remote_url_as_template_source(doctor, tmp_path, capsys, no_template_env):
    _write_hook_config(tmp_path, "config.json", {"ai_template_path": "https://example.com/template.git"})
    doctor.check_claude_template_path()
    out = capsys.readouterr().out
    assert "✓" in out and "remote, from config.json" in out


def test_should_warn_when_configured_path_does_not_exist(doctor, tmp_path, capsys, no_template_env):
    _write_hook_config(tmp_path, "config.json", {"ai_template_path": str(tmp_path / "missing")})
    doctor.check_claude_template_path()
    out = capsys.readouterr().out
    assert "⚠" in out and "doesn't exist" in out and "from config.json" in out


def test_should_warn_when_no_source_is_set(doctor, tmp_path, capsys, no_template_env):
    _write_hook_config(tmp_path, "config.json", {"lint": "x"})
    doctor.check_claude_template_path()
    out = capsys.readouterr().out
    assert "⚠" in out and "ai_template_path not set" in out and "config.local.json" in out


def test_should_say_repo_is_template_when_marked(doctor, tmp_path, capsys, no_template_env):
    _write_hook_config(tmp_path, "config.json", {"is_template": True})
    doctor.check_claude_template_path()
    out = capsys.readouterr().out
    assert "✓" in out and "is the AI template" in out and "⚠" not in out


def test_should_ignore_unparseable_local_file_and_say_so(doctor, tmp_path, capsys, no_template_env):
    _write_hook_config(tmp_path, "config.json", {"ai_template_path": "https://example.com/template.git"})
    _write_hook_config(tmp_path, "config.local.json", "{ not json")
    doctor.check_claude_template_path()
    out = capsys.readouterr().out
    assert "config.local.json present but unparseable" in out
    assert "remote, from config.json" in out


# ── main: exit code ──────────────────────────────────────────────────────────

REQUIRED_ELSEWHERE = ["check_python", "check_node", "check_pre_commit", "check_hooks_installed", "check_config_yaml"]
OPTIONAL = ["check_claude_template_path", "check_docker", "check_git_branch"]


@pytest.fixture()
def doctor_rest_green(doctor, monkeypatch):
    """Every check except the Claude Code hooks and pytest ones is stubbed out as passing."""
    monkeypatch.setattr(doctor, "run", lambda cmd: (0, "pytest 8.0.0"))
    for name in REQUIRED_ELSEWHERE:
        monkeypatch.setattr(doctor, name, lambda: True)
    for name in OPTIONAL:
        monkeypatch.setattr(doctor, name, lambda: None)
    return doctor


def test_should_exit_1_when_placeholder_is_left(doctor_rest_green, tmp_path):
    _write_local(tmp_path, _settings(interpreter="INTERPRETER"))
    assert doctor_rest_green.main() == 1


def test_should_exit_0_when_settings_file_is_missing(doctor_rest_green):
    assert doctor_rest_green.main() == 0


def test_should_exit_0_when_pytest_is_missing(doctor_rest_green, tmp_path, monkeypatch):
    _write_local(tmp_path, _settings())
    monkeypatch.setattr(doctor_rest_green, "run", lambda cmd: (1, ""))
    assert doctor_rest_green.main() == 0


# ── GitHub repository settings (docs/SETUP.md step 1) ────────────────────────

def _gh(results):
    def run(command):
        text = " ".join(command)
        for prefix, result in results.items():
            if text.startswith(prefix):
                return result
        return 1, ""
    return run


def _release_workflow(root):
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "release-please.yml").write_text("name: release\n", encoding="utf-8")


def test_should_warn_when_repo_settings_are_at_github_defaults(doctor, tmp_path, monkeypatch, capsys):
    _release_workflow(tmp_path)
    monkeypatch.setattr(doctor, "run", _gh({
        "gh repo view": (0, "acme/shop\n"),
        "gh api repos/acme/shop/actions/permissions/workflow": (0, "read false\n"),
        "gh api repos/acme/shop": (0, "false\n"),
    }))
    doctor.repo_settings.doctor_check(tmp_path, doctor.run, doctor.ok, doctor.warn)
    out = capsys.readouterr().out
    assert "⚠" in out and "kasowanie gałęzi" in out and "uprawnienia automatów" in out
    assert "project-setup.py" in out


def test_should_report_repo_settings_in_place(doctor, tmp_path, monkeypatch, capsys):
    _release_workflow(tmp_path)
    monkeypatch.setattr(doctor, "run", _gh({
        "gh repo view": (0, "acme/shop\n"),
        "gh api repos/acme/shop/actions/permissions/workflow": (0, "write true\n"),
        "gh api repos/acme/shop": (0, "true\n"),
    }))
    doctor.repo_settings.doctor_check(tmp_path, doctor.run, doctor.ok, doctor.warn)
    out = capsys.readouterr().out
    assert "✓" in out and "acme/shop" in out and "⚠" not in out


def test_should_say_nothing_about_repo_settings_without_a_github_repo(doctor, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run", _gh({"gh repo view": (1, "no git remotes")}))
    doctor.repo_settings.doctor_check(tmp_path, doctor.run, doctor.ok, doctor.warn)
    assert capsys.readouterr().out == ""


def test_should_never_fail_doctor_because_of_repo_settings(doctor_rest_green, tmp_path, monkeypatch):
    _write_local(tmp_path, _settings())
    monkeypatch.setattr(doctor_rest_green, "run", _gh({
        "gh repo view": (0, "acme/shop\n"),
        "gh api repos/acme/shop/actions/permissions/workflow": (0, "read false\n"),
        "gh api repos/acme/shop": (0, "false\n"),
    }))
    assert doctor_rest_green.main() == 0
