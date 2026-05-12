#!/usr/bin/env python3
"""
Guard 1: Format commita + lint + testy.
Blokuje (exit 2 + stderr) git commit jeśli:
- wiadomość nie spełnia formatu type(scope): opis
- lint failuje
- testy failują

Nieznany stack: ostrzega na stdout, nie blokuje.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, cmd_exists, detect_stack, get_lint_cmd, get_staged_files, get_test_cmd, is_foreign_repo, is_git_commit_command, run_cmd


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def extract_commit_message(command: str) -> str:
    m = re.search(r'-m\s+"([^"]+)"', command)
    if m:
        return m.group(1)
    m = re.search(r"-m\s+'([^']+)'", command)
    if m:
        return m.group(1)
    m = re.search(r"<<['\"]?EOF['\"]?\s*\n(.*?)\nEOF", command, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def block(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(2)


def main():
    command = get_command()
    chdir_to_project_root(command)

    if not is_git_commit_command(command):
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    # 0. Branch check — block commits directly on main/master
    result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    current_branch = result.stdout.strip()
    if current_branch in ("main", "master"):
        block(
            "❌ [BLOCK] Jesteś na branchu 'main' — nie commituj bezpośrednio.\n"
            "   Utwórz branch: git checkout -b feat/nazwa  lub  fix/nazwa"
        )

    # 1. Format commita
    msg = extract_commit_message(command)
    if not msg:
        block("❌ [BLOCK] Nie wykryto wiadomości commita (-m '...' lub heredoc).")

    first_line = msg.split("\n")[0].strip()
    pattern = r"^(feat|fix|docs|refactor|test|chore|style|perf|ci|build)(\([a-zA-Z0-9_/.-]+\))?!?:\s.{3,}"
    if not re.match(pattern, first_line):
        block(
            f"❌ [BLOCK] Zły format commita: '{first_line}'\n"
            "   Wymagany: type(scope): opis  (min 3 znaki opisu)\n"
            "   Typy: feat | fix | docs | refactor | test | chore | style | perf | ci | build"
        )

    # 2. Stack
    stack = detect_stack()
    lint_cmd = get_lint_cmd()
    test_cmd = get_test_cmd()

    if stack == "unknown" and not lint_cmd:
        print(
            "⚠️  [WARN] Nieznany stack — lint i testy pominięte.\n"
            "   Skonfiguruj .claude/hooks/config.json\n"
            '   Przykład: { "lint": "composer lint", "test": "composer test" }'
        )
        sys.exit(0)

    # 3. Lint
    if lint_cmd:
        if not cmd_exists(lint_cmd):
            print(f"⚠️  [WARN] Lint niedostępny: {' '.join(lint_cmd)}")
        else:
            print(f"🔍 Lint [{stack}]...", flush=True)
            code, output = run_cmd(lint_cmd)
            if code != 0:
                block(f"❌ [BLOCK] Lint failed:\n{output}")

    # 4. Testy (tylko gdy pliki źródłowe w staged)
    if test_cmd:
        staged = get_staged_files(command)
        src_ext = (".ts", ".tsx", ".php", ".py", ".rb", ".go", ".js", ".jsx")
        if any(f.endswith(src_ext) for f in staged):
            if not cmd_exists(test_cmd):
                print(f"⚠️  [WARN] Test niedostępny: {' '.join(test_cmd)}")
            else:
                print(f"🔍 Testy [{stack}]...", flush=True)
                code, output = run_cmd(test_cmd)
                if code != 0:
                    block(f"❌ [BLOCK] Testy failed:\n{output}")

    print(f"✅ pre-commit OK [{stack}]: format ✓  lint ✓  testy ✓")
    sys.exit(0)


if __name__ == "__main__":
    main()
