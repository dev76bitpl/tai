"""Tests for scripts/validate-skills.py"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "validate-skills.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_skills", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
parse_frontmatter = mod.parse_frontmatter
validate_skill = mod.validate_skill


# ── parse_frontmatter ────────────────────────────────────────────────────────

class TestParseFrontmatter:
    def test_valid(self):
        content = '---\nname: my-skill\ndescription: "Does something"\n---\n# Body'
        result = parse_frontmatter(content)
        assert result == {"name": "my-skill", "description": "Does something"}

    def test_no_frontmatter(self):
        assert parse_frontmatter("# Just markdown") is None

    def test_empty_frontmatter_block(self):
        # regex requires at least one \n between delimiters, so ---\n--- returns None
        assert parse_frontmatter("---\n---\n# Body") is None

    def test_strips_quotes(self):
        content = "---\nname: 'single'\ndescription: \"double\"\n---"
        result = parse_frontmatter(content)
        assert result["name"] == "single"
        assert result["description"] == "double"

    def test_multiline_body_ignored(self):
        content = "---\nname: skill\n---\n## Section\nsome: value"
        result = parse_frontmatter(content)
        assert "some" not in result

    def test_missing_closing_delimiter(self):
        assert parse_frontmatter("---\nname: skill\n") is None


# ── validate_skill ───────────────────────────────────────────────────────────

class TestValidateSkill:
    def _make_skill(self, tmp_path: Path, name: str, content: str) -> Path:
        skill_dir = tmp_path / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        return skill_dir

    def test_valid_skill(self, tmp_path):
        skill_dir = self._make_skill(
            tmp_path, "my-skill",
            '---\nname: my-skill\ndescription: "Short description"\n---\n# Body'
        )
        assert validate_skill(skill_dir, strict=False) == []

    def test_missing_skill_md(self, tmp_path):
        skill_dir = tmp_path / "orphan"
        skill_dir.mkdir()
        errors = validate_skill(skill_dir, strict=False)
        assert any("missing SKILL.md" in e for e in errors)

    def test_no_frontmatter(self, tmp_path):
        skill_dir = self._make_skill(tmp_path, "bad", "# No frontmatter here")
        errors = validate_skill(skill_dir, strict=False)
        assert any("no YAML frontmatter" in e for e in errors)

    def test_missing_name_field(self, tmp_path):
        skill_dir = self._make_skill(
            tmp_path, "no-name",
            '---\ndescription: "Something"\n---\n'
        )
        errors = validate_skill(skill_dir, strict=False)
        assert any("missing required field 'name'" in e for e in errors)

    def test_missing_description_field(self, tmp_path):
        skill_dir = self._make_skill(
            tmp_path, "no-desc",
            '---\nname: no-desc\n---\n'
        )
        errors = validate_skill(skill_dir, strict=False)
        assert any("missing required field 'description'" in e for e in errors)

    def test_name_mismatch(self, tmp_path):
        skill_dir = self._make_skill(
            tmp_path, "actual-name",
            '---\nname: wrong-name\ndescription: "Something"\n---\n'
        )
        errors = validate_skill(skill_dir, strict=False)
        assert any("does not match directory name" in e for e in errors)

    def test_strict_description_too_long(self, tmp_path):
        long_desc = "x" * 301
        skill_dir = self._make_skill(
            tmp_path, "verbose",
            f'---\nname: verbose\ndescription: "{long_desc}"\n---\n'
        )
        errors_normal = validate_skill(skill_dir, strict=False)
        errors_strict = validate_skill(skill_dir, strict=True)
        assert errors_normal == []
        assert any("chars" in e and "max" in e for e in errors_strict)

    def test_strict_description_ok_length(self, tmp_path):
        desc = "x" * 100
        skill_dir = self._make_skill(
            tmp_path, "short",
            f'---\nname: short\ndescription: "{desc}"\n---\n'
        )
        assert validate_skill(skill_dir, strict=True) == []

    def test_empty_name_field(self, tmp_path):
        skill_dir = self._make_skill(
            tmp_path, "empty-name",
            '---\nname: \ndescription: "Something"\n---\n'
        )
        errors = validate_skill(skill_dir, strict=False)
        # name field is absent in parse result (no value after colon+space)
        assert len(errors) > 0
