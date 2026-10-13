"""The suite must never reach the real repository when it runs from a git hook.

Regression: committing from a linked worktree ran these tests with GIT_DIR and GIT_INDEX_FILE
pointing at the real repository; tests that start `git` in a temp directory flipped core.bare
in the real config and staged their fixtures into the real index. conftest.py now strips every
GIT_* variable before each test.
"""
import os
import subprocess


def test_should_not_see_git_variables_inherited_from_a_hook():
    assert [key for key in os.environ if key.startswith("GIT_")] == []


def test_should_start_git_in_the_temp_directory_not_in_the_calling_repository(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    assert os.path.realpath(top) == os.path.realpath(tmp_path)
