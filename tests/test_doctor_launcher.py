"""Tests for scripts/doctor.mjs — the cross-platform launcher behind `npm run doctor`.

Regression for `python3 scripts/doctor.py || py scripts/doctor.py`: doctor exits 1 on purpose
when a required check fails, and the shell `||` read that as "python3 missing" and fell through
to the Windows `py` launcher. On Linux/WSL every red report ended with a misleading
`py: not found`; on Windows the report ran twice.

The launcher must run doctor exactly once, forward its exit code untouched and say plainly when
no Python is reachable. Tests drive the real script through `node` with a controlled PATH.
"""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "scripts" / "doctor.mjs"
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.skipif(NODE is None, reason="node not on PATH"),
    pytest.mark.skipif(sys.platform == "win32", reason="fake interpreter is a POSIX shell script"),
]


def _run(path_dirs):
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([*path_dirs, str(Path(NODE).parent)])
    return subprocess.run(
        [NODE, str(LAUNCHER)], capture_output=True, text=True, env=env, cwd=ROOT, check=False
    )


def _fake_python3(directory: Path, body: str) -> None:
    fake = directory / "python3"
    fake.write_text(
        '#!/bin/sh\ncase "$1" in\n  --version) echo "Python 3.12.0" ;;\n  *) ' + body + " ;;\nesac\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)


def test_should_run_doctor_once_and_forward_exit_code_when_report_is_red(tmp_path):
    _fake_python3(tmp_path, 'echo "REPORT: ${1##*/}"; exit 1')

    result = _run([str(tmp_path)])

    assert result.returncode == 1
    assert result.stdout.count("REPORT: doctor.py") == 1
    assert "py: not found" not in result.stderr


def test_should_forward_zero_when_report_is_green(tmp_path):
    _fake_python3(tmp_path, 'echo "REPORT: ok"; exit 0')

    result = _run([str(tmp_path)])

    assert result.returncode == 0
    assert result.stdout.count("REPORT: ok") == 1


def test_should_fail_with_clear_message_when_no_python_on_path(tmp_path):
    result = _run([str(tmp_path)])

    assert result.returncode == 1
    assert "No Python interpreter found" in result.stderr
