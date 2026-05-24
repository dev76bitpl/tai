#!/usr/bin/env python3
"""
Validates SKILL.md frontmatter for all skills in .claude/skills/.

Usage:
    python3 scripts/validate-skills.py           # validate all skills
    python3 scripts/validate-skills.py --strict  # also check description length

Exit codes: 0 = all valid, 1 = validation errors found.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / ".claude" / "skills"

REQUIRED_FIELDS = ["name", "description"]
MAX_DESCRIPTION_LENGTH = 300


def parse_frontmatter(content: str) -> dict[str, str] | None:
    """Extracts YAML frontmatter fields as key-value strings. Returns None if no frontmatter."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    fields: dict[str, str] = {}
    block = match.group(1)

    for line in block.splitlines():
        kv_match = re.match(r'^(\w[\w-]*):\s*(.+)', line)
        if kv_match:
            key = kv_match.group(1)
            value = kv_match.group(2).strip().strip('"').strip("'")
            fields[key] = value

    return fields


def validate_skill(skill_dir: Path, strict: bool) -> list[str]:
    """Validates a single skill directory. Returns list of error messages."""
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        errors.append(f"{skill_dir.name}: missing SKILL.md")
        return errors

    content = skill_md.read_text(encoding="utf-8")
    fields = parse_frontmatter(content)

    if fields is None:
        errors.append(f"{skill_dir.name}: SKILL.md has no YAML frontmatter (expected --- block)")
        return errors

    for field in REQUIRED_FIELDS:
        if field not in fields:
            errors.append(f"{skill_dir.name}: frontmatter missing required field '{field}'")
        elif not fields[field].strip():
            errors.append(f"{skill_dir.name}: frontmatter field '{field}' is empty")

    if strict and "description" in fields:
        desc_len = len(fields["description"])
        if desc_len > MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"{skill_dir.name}: description is {desc_len} chars "
                f"(max {MAX_DESCRIPTION_LENGTH} in strict mode)"
            )

    if "name" in fields:
        expected_name = skill_dir.name
        actual_name = fields["name"]
        if actual_name != expected_name:
            errors.append(
                f"{skill_dir.name}: frontmatter name '{actual_name}' "
                f"does not match directory name '{expected_name}'"
            )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate SKILL.md frontmatter")
    parser.add_argument("--strict", action="store_true", help="Also check description length")
    args = parser.parse_args()

    if not SKILLS_DIR.is_dir():
        print(f"❌ Skills directory not found: {SKILLS_DIR}")
        sys.exit(1)

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())

    if not skill_dirs:
        print("⚠️  No skill directories found.")
        sys.exit(0)

    all_errors: list[str] = []

    for skill_dir in skill_dirs:
        errors = validate_skill(skill_dir, args.strict)
        all_errors.extend(errors)

    total = len(skill_dirs)

    if all_errors:
        print(f"❌ Validation failed — {len(all_errors)} error(s) in {total} skill(s):\n")
        for err in all_errors:
            print(f"  • {err}")
        sys.exit(1)
    else:
        mode = " (strict)" if args.strict else ""
        print(f"✅ All {total} skill(s) valid{mode}.")
        sys.exit(0)


if __name__ == "__main__":
    main()
