"""Tests for .claude/hooks/stack.py — rozstrzyganie ścieżki do template.

Powód istnienia: ai_template_path był czytany wyłącznie z commitowanego
config.json, więc każdy klon wymagał wpisania ścieżki z konkretnej maszyny,
a ta ścieżka wjeżdżała do repo. Resolver dokłada warstwy: env, config.local.json,
autodetekcja klona obok (po markerze, nie po nazwie — repo ai zostało
przemianowane na tai) i publiczny URL jako ostatnia deska ratunku.
"""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STACK = ROOT / ".claude" / "hooks" / "stack.py"


def _load_at(project_root: Path):
    """Ładuje stack.py tak, jakby leżał w <project_root>/.claude/hooks/.

    Dzięki temu load_config() i get_hooks_root() widzą drzewo testowe,
    a nie prawdziwe repo.
    """
    hooks = project_root / ".claude" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    target = hooks / "stack.py"
    shutil.copy(STACK, target)
    spec = importlib.util.spec_from_file_location(f"stack_{project_root.name}", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_config(project_root: Path, name: str, data: dict) -> None:
    path = project_root / ".claude" / "hooks" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_template_clone(path: Path, *, is_template: bool = True, manifest: bool = True) -> Path:
    """Klon template rozpoznawany po zawartości. Nazwa katalogu dowolna."""
    (path / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    _write_config(path, "config.json", {"is_template": is_template} if is_template else {})
    if manifest:
        (path / "skills-manifest.json").write_text("{}", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("AI_TEMPLATE_PATH", raising=False)


@pytest.fixture
def project(tmp_path):
    """Projekt w workspace, żeby rodzeństwo katalogów było kontrolowane."""
    workspace = tmp_path / "workspace"
    root = workspace / "some-project"
    root.mkdir(parents=True)
    return root


# ── kolejność warstw ──────────────────────────────────────────────────────────

class TestPrecedence:
    def test_env_wins_over_config(self, project, monkeypatch):
        mod = _load_at(project)
        _write_config(project, "config.json", {"ai_template_path": "/z/configu"})
        monkeypatch.setenv("AI_TEMPLATE_PATH", "/z/env")
        assert mod.resolve_template_source() == ("/z/env", "$AI_TEMPLATE_PATH")

    def test_config_local_wins_over_config(self, project):
        mod = _load_at(project)
        _write_config(project, "config.json", {"ai_template_path": "/z/configu"})
        _write_config(project, "config.local.json", {"ai_template_path": "/z/local"})
        assert mod.resolve_template_path() == "/z/local"

    def test_config_used_when_no_env(self, project):
        mod = _load_at(project)
        _write_config(project, "config.json", {"ai_template_path": "/z/configu"})
        assert mod.resolve_template_source() == ("/z/configu", "config.json")

    def test_falls_back_to_default_url(self, project):
        mod = _load_at(project)
        value, source = mod.resolve_template_source()
        assert value == mod.DEFAULT_TEMPLATE_URL
        assert source == "default"

    def test_empty_values_are_ignored(self, project):
        """Puste pole nie może zablokować dalszych warstw."""
        mod = _load_at(project)
        _write_config(project, "config.json", {"ai_template_path": "   "})
        assert mod.resolve_template_path() == mod.DEFAULT_TEMPLATE_URL


# ── autodetekcja: po markerze, nie po nazwie ──────────────────────────────────

class TestAutodetect:
    def test_finds_clone_regardless_of_directory_name(self, project):
        """Sedno zmiany: nazwa katalogu i repo nie ma znaczenia."""
        mod = _load_at(project)
        clone = _make_template_clone(project.parent / "zupelnie-inna-nazwa")
        assert mod.resolve_template_source() == (str(clone), "autodetekcja")

    def test_ignores_sibling_without_is_template(self, project):
        mod = _load_at(project)
        _make_template_clone(project.parent / "inny-projekt", is_template=False)
        assert mod.resolve_template_path() == mod.DEFAULT_TEMPLATE_URL

    def test_ignores_sibling_without_manifest(self, project):
        mod = _load_at(project)
        _make_template_clone(project.parent / "pol-template", manifest=False)
        assert mod.resolve_template_path() == mod.DEFAULT_TEMPLATE_URL

    def test_does_not_detect_itself(self, project):
        """Projekt będący template'm nie może wskazywać sam na siebie."""
        mod = _load_at(project)
        _make_template_clone(project)
        assert mod.resolve_template_path() == mod.DEFAULT_TEMPLATE_URL

    def test_config_wins_over_autodetect(self, project):
        mod = _load_at(project)
        _make_template_clone(project.parent / "tai")
        _write_config(project, "config.json", {"ai_template_path": "/jawnie/wskazany"})
        assert mod.resolve_template_path() == "/jawnie/wskazany"


# ── _is_template_root ─────────────────────────────────────────────────────────

class TestIsTemplateRoot:
    def test_accepts_marked_clone(self, project):
        mod = _load_at(project)
        clone = _make_template_clone(project.parent / "x")
        assert mod._is_template_root(clone) is True

    def test_rejects_missing_directory(self, project):
        mod = _load_at(project)
        assert mod._is_template_root(project.parent / "nie-ma") is False

    def test_rejects_broken_json(self, project):
        mod = _load_at(project)
        clone = project.parent / "zepsuty"
        (clone / ".claude" / "hooks").mkdir(parents=True)
        (clone / "skills-manifest.json").write_text("{}", encoding="utf-8")
        (clone / ".claude" / "hooks" / "config.json").write_text("{ nie json", encoding="utf-8")
        assert mod._is_template_root(clone) is False


# ── load_config ───────────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_merges_local_over_shared(self, project):
        mod = _load_at(project)
        _write_config(project, "config.json", {"lint": "a", "test": "wspolny"})
        _write_config(project, "config.local.json", {"lint": "b"})
        config = mod.load_config()
        assert config["lint"] == "b"
        assert config["test"] == "wspolny"

    def test_broken_local_does_not_kill_shared(self, project):
        mod = _load_at(project)
        _write_config(project, "config.json", {"lint": "a"})
        (project / ".claude" / "hooks" / "config.local.json").write_text("{ zepsuty", encoding="utf-8")
        assert mod.load_config()["lint"] == "a"

    def test_no_config_returns_empty(self, project):
        mod = _load_at(project)
        assert mod.load_config() == {}


# ── is_template_url ───────────────────────────────────────────────────────────

class TestIsTemplateUrl:
    @pytest.mark.parametrize("value", [
        "https://github.com/dev76bitpl/tai.git",
        "http://example.com/x.git",
        "git@github-76bit:dev76bitpl/tai.git",
        "ssh://git@example.com/x.git",
    ])
    def test_urls(self, project, value):
        mod = _load_at(project)
        assert mod.is_template_url(value) is True

    @pytest.mark.parametrize("value", ["/home/user/Projekty/tai", "../tai", "tai"])
    def test_paths(self, project, value):
        mod = _load_at(project)
        assert mod.is_template_url(value) is False
