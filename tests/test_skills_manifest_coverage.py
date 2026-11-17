"""Every skill Claude Code can see is tracked in skills-manifest.json, and every tracked one is visible.

Claude Code loads a skill only from `.claude/skills/<name>/SKILL.md`. web-quality-skills used to live
in `.claude/skills/perf/<name>/` with hand-made visible copies next to it: the update refreshed
`perf/*`, the copies Claude really used went stale, and the sync never looked at them (#228).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"


def _manifest_dirs() -> dict[str, str]:
    """skill directory name -> manifest entry that owns it."""
    manifest = json.loads((ROOT / "skills-manifest.json").read_text(encoding="utf-8"))
    dirs = {name: f"custom_skills.{name}" for name in manifest["custom_skills"]}
    for name, entry in manifest["skills"].items():
        local = Path(entry.get("local_path", f".claude/skills/{name}"))
        assert local.parent == Path(".claude/skills"), f"{name}: {local} is not where Claude Code looks for skills"
        dirs[local.name] = f"skills.{name}"
    return dirs


def test_should_track_every_skill_claude_code_can_see():
    visible = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
    assert sorted(visible - set(_manifest_dirs())) == []


def test_should_make_every_tracked_skill_visible_to_claude_code():
    missing = {owner for name, owner in _manifest_dirs().items() if not (SKILLS / name / "SKILL.md").is_file()}
    assert sorted(missing) == []


def test_should_not_keep_skills_nested_where_claude_code_does_not_look():
    nested = sorted(str(p.relative_to(SKILLS)) for p in SKILLS.glob("*/*/SKILL.md"))
    assert nested == []
