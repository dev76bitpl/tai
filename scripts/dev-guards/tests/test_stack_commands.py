"""Tests for how the lint and test guards pick their command (scripts/dev-guards/stack.py).

A fresh project used to inherit "composer lint" / "composer test" from the example config, so
its guards warned invisibly and checked nothing. The command now comes from the project's own
files unless the project names one itself, and `npm run doctor` shows what will really run.
"""
import json
import subprocess
import sys

from harness import clean_env, stage, write_config

SNIPPET = """
import json, sys
sys.path.insert(0, "scripts/dev-guards")
import stack
print(json.dumps({"lint": stack.get_cmd("lint"), "test": stack.get_cmd("test"), "doctor": stack.doctor_lines()}))
"""


def _inspect(repo) -> dict:
    result = subprocess.run([sys.executable, "-c", SNIPPET], cwd=repo, env=clean_env(),
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_should_autodetect_commands_from_project_files_when_config_names_none(repo):
    stage(repo, "composer.json", '{"scripts": {"lint": "x", "test": "y"}}\n')
    write_config(repo, {"src_dirs": ["app"]})
    data = _inspect(repo)
    assert data["lint"] == [["composer", "lint"], False]
    assert data["test"] == [["composer", "test"], False]


def test_should_mark_command_from_config_as_explicit(repo):
    write_config(repo, {"lint": "python3 -m compileall -q ."})
    assert _inspect(repo)["lint"] == [["python3", "-m", "compileall", "-q", "."], True]


def test_should_tell_doctor_that_a_fresh_node_project_checks_nothing(repo):
    stage(repo, "package.json", '{"scripts": {"doctor": "node x.mjs"}}\n')
    lines = _inspect(repo)["doctor"]
    assert [fine for fine, _, _ in lines] == [False, False]
    assert "Lint guard checks nothing: npm run lint --silent (autodetected: node)" in lines[0][1]
    assert 'has no "lint" script' in lines[0][1] and 'has no "test" script' in lines[1][1]


def test_should_tell_doctor_which_commands_run_when_they_are_available(repo):
    write_config(repo, {"lint": "python3 --version", "test": "python3 --version"})
    lines = _inspect(repo)["doctor"]
    assert [fine for fine, _, _ in lines] == [True, True]
    assert "Lint guard runs: python3 --version  (config.json)" == lines[0][1]


def test_should_tell_doctor_that_an_explicit_broken_command_blocks_commits(repo):
    write_config(repo, {"lint": "no-such-linter-xyz"})
    fine, message, _ = _inspect(repo)["doctor"][0]
    assert fine is False and "BLOCKS every commit" in message and "config.json" in message


def test_should_tell_doctor_about_unknown_stack(repo):
    lines = _inspect(repo)["doctor"]
    assert all("unknown stack" in message for _, message, _ in lines)


def test_should_take_commands_from_the_configured_stack_over_the_template_package_json(repo):
    # every project starts with the template's package.json — detection alone said "node" (#193)
    stage(repo, "package.json", '{"scripts": {"doctor": "node x.mjs"}}\n')
    write_config(repo, {"stack": "python"})
    data = _inspect(repo)
    assert data["lint"] == [["ruff", "check", "."], False]
    assert data["test"] == [["pytest", "--tb=short", "-q"], False]
    assert all("(stack: python)" in message for _, message, _ in data["doctor"])


def test_should_map_a_platform_stack_to_its_toolchain(repo):
    stage(repo, "package.json", "{}\n")
    write_config(repo, {"stack": "laravel"})
    assert _inspect(repo)["lint"] == [["composer", "lint"], False]


def test_should_fall_back_to_detection_when_the_stack_is_other(repo):
    stage(repo, "package.json", "{}\n")
    write_config(repo, {"stack": "inny"})
    assert _inspect(repo)["lint"] == [["npm", "run", "lint", "--silent"], False]


def test_should_know_the_toolchain_of_every_stack_the_interview_can_set():
    import importlib.util
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("set_stack_for_guards", root / "scripts" / "set-stack.py")
    set_stack = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(set_stack)
    spec = importlib.util.spec_from_file_location("dev_guards_stack", root / "scripts" / "dev-guards" / "stack.py")
    stack = importlib.util.module_from_spec(spec)  # "stack" alone may resolve to .claude/hooks/stack.py
    spec.loader.exec_module(stack)
    missing = set(set_stack.STACK_PRESETS) - set(stack.CONFIGURED_STACKS) - {set_stack.DEFAULT_STACK}
    assert not missing, f"stacks without guard commands: {missing}"
    assert set(stack.CONFIGURED_STACKS.values()) <= set(stack.STACKS)
