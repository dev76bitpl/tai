"""Tests for the personal-data detector (scripts/dev-guards/pii.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "dev-guards"))
from pii import account_ok, mask, pesel_ok, scan_line  # noqa: E402


def kinds(line, names=()):
    return [k for k, _ in scan_line(line, names)]


def test_valid_pesel_found_invalid_ignored():
    assert pesel_ok("44051401359")  # pii-ok
    assert kinds("uczen 44051401359") == ["PESEL"]  # pii-ok
    assert kinds("id 44051401358") == []          # pii-ok, bad checksum
    assert kinds("ts 17278364001234") == []       # pii-ok, longer number


def test_bank_account_checksum():
    acc = "61109010140000071219812874"  # pii-ok
    assert account_ok(acc)
    assert "bank account" in kinds("konto PL61 1090 1014 0000 0712 1981 2874")  # pii-ok
    assert kinds("konto 61109010140000071219812875") == []  # pii-ok


def test_phone_formats():
    assert kinds("tel. +48 600 700 800") == ["phone"]  # pii-ok
    assert kinds("tel. 600-700-800") == ["phone"]  # pii-ok
    assert kinds("version 1.600.700") == []


def test_private_vs_company_email():
    assert kinds("jan.kowalski@gmail.com") == ["private e-mail"]  # pii-ok
    assert kinds("biuro@cdue.edu.pl") == []
    assert kinds("user@example.com") == []


def test_names_from_list_whole_word():
    assert kinds("Ania Zielinska zapisana", ["Zielinska"]) == ["listed name"]  # pii-ok
    assert kinds("ZielinskaService", ["Zielinska"]) == []  # pii-ok


def test_marker_skips_line_and_values_are_masked():
    assert kinds("fake 44051401359 pii-ok") == []
    assert mask("44051401359") == "44*******59"  # pii-ok
    assert all("*" in v for _, v in scan_line("44051401359 jan@gmail.com"))  # pii-ok


def test_phone_noise_ignored():
    assert kinds("color: 255 255 255") == []
    assert kinds("size 1 073 741 824 bytes") == []
    assert kinds("placeholder 600 000 000") == []  # pii-ok


# --- the guard itself: staged diff in, exit code out ---------------------------------------

import os  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402

GUARD = Path(__file__).resolve().parents[1] / "scripts" / "dev-guards" / "guard_pii.py"
FAKE_PESEL = "44051401359"  # pii-ok


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def stage(repo, name, text):
    (repo / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "--", name], cwd=repo, check=True)


def run_guard(cwd, **extra_env):
    env = dict(os.environ, PII_NAMES_FILE=str(cwd / "no-names"), PII_PUBLIC_FILE=str(cwd / "no-public"))
    for var in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):  # set when run from a git hook
        env.pop(var, None)
    env.update(extra_env)
    return subprocess.run([sys.executable, str(GUARD)], cwd=cwd, env=env,
                          capture_output=True, text=True, encoding="utf-8")


def test_should_block_and_mask_when_staged_line_adds_pesel(repo):
    stage(repo, "notes.txt", "first line\nstudent %s\n" % FAKE_PESEL)
    result = run_guard(repo)
    assert result.returncode == 1
    assert "notes.txt:2" in result.stderr
    assert "PESEL" in result.stderr
    assert FAKE_PESEL not in result.stderr


def test_should_pass_when_staged_change_is_clean(repo):
    stage(repo, "notes.txt", "nothing personal here\nversion 1.600.700\n")
    result = run_guard(repo)
    assert result.returncode == 0
    assert result.stderr == ""


def test_should_pass_when_nothing_is_staged(repo):
    assert run_guard(repo).returncode == 0


def test_should_pass_when_line_is_marked_as_fake_data(repo):
    stage(repo, "fixture.txt", "student %s pii-ok\n" % FAKE_PESEL)
    assert run_guard(repo).returncode == 0


def test_should_block_when_file_name_has_non_ascii_characters(repo):
    stage(repo, "zażółć.txt", "student %s\n" % FAKE_PESEL)
    result = run_guard(repo)
    assert result.returncode == 1
    assert "zażółć.txt:1" in result.stderr


def test_should_block_when_file_name_has_space(repo):
    stage(repo, "class list.txt", "student %s\n" % FAKE_PESEL)
    result = run_guard(repo)
    assert result.returncode == 1
    assert "class list.txt:1" in result.stderr


def test_should_block_when_added_line_looks_like_diff_header(repo):
    stage(repo, "notes.txt", "++ /dev/null\nstudent %s\n" % FAKE_PESEL)
    result = run_guard(repo)
    assert result.returncode == 1
    assert "notes.txt:2" in result.stderr


def test_should_skip_lock_files(repo):
    stage(repo, "package-lock.json", '{"integrity": "%s"}\n' % FAKE_PESEL)
    assert run_guard(repo).returncode == 0


def test_should_block_when_staged_diff_cannot_be_read(tmp_path):
    result = run_guard(tmp_path, GIT_DIR=str(tmp_path / "missing.git"))
    assert result.returncode == 1
    assert "[BLOCK]" in result.stderr
