"""Tests for .claude/hooks/sync_ack.py: how a commit acknowledges a template desync (tai#243)."""
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))
import sync_ack as s  # noqa: E402


def fake_run(returncode=0, stdout="", stderr="", raises=None, calls=None):
    def run(args, **_):
        if calls is not None:
            calls.append(args)
        if raises:
            raise raises
        return subprocess.CompletedProcess(args, returncode, stdout, stderr)
    return run


class TestTaiRefs:
    def test_finds_short_and_full_references(self):
        assert s.tai_refs("fix: x\n\nRefs tai#12, dev76bitpl/tai#5 and tai#12") == [5, 12]

    def test_ignores_other_names_and_suffixes(self):
        assert s.tai_refs("mytai#3 tai-x#4 tai#5a #6") == []


class TestSkipReason:
    def test_none_without_flag(self):
        assert s.skip_reason("docs: x") is None

    def test_text_after_flag_on_its_line(self):
        assert s.skip_reason("docs: x\n\n[skip-sync] pricing is CRM only\nmore") == "pricing is CRM only"

    def test_reason_needs_three_words(self):
        assert s.has_reason("pricing is CRM-only") is True
        assert s.has_reason("CRM only") is False
        assert s.has_reason("") is False
        assert s.has_reason(None) is False

    def test_reason_on_the_next_line_does_not_count(self):
        assert s.has_reason(s.skip_reason("[skip-sync]\nbecause this is ours")) is False


class TestRepoSlug:
    def test_https_url(self):
        assert s.repo_slug("https://github.com/acme/tai.git") == "acme/tai"

    def test_local_clone_with_ssh_alias(self):
        run = fake_run(stdout="github-76bit:dev76bitpl/tai.git\n")
        assert s.repo_slug("/home/x/tai", run) == "dev76bitpl/tai"

    def test_local_clone_without_remote_falls_back(self):
        assert s.repo_slug("/nowhere", fake_run(returncode=2)) == s.DEFAULT_REPO

    def test_empty_falls_back(self):
        assert s.repo_slug("") == s.DEFAULT_REPO


class TestRefExists:
    def test_found(self):
        calls = []
        assert s.ref_exists("acme/tai", 7, fake_run(stdout="7", calls=calls)) is True
        assert calls[0][:3] == ["gh", "api", "repos/acme/tai/issues/7"]

    def test_not_found(self):
        assert s.ref_exists("acme/tai", 7, fake_run(1, stderr="gh: Not Found (HTTP 404)")) is False

    def test_offline_is_unknown(self):
        assert s.ref_exists("acme/tai", 7, fake_run(1, stderr="error connecting")) is None

    def test_no_gh_is_unknown(self):
        assert s.ref_exists("acme/tai", 7, fake_run(raises=FileNotFoundError())) is None

    def test_timeout_is_unknown(self):
        assert s.ref_exists("acme/tai", 7, fake_run(raises=subprocess.TimeoutExpired("gh", 5))) is None


class TestAcknowledge:
    def test_nothing_in_message(self):
        assert s.acknowledge("docs: x", "a/tai").status == s.NONE

    def test_existing_reference_passes_quietly(self):
        ack = s.acknowledge("docs: x tai#7", "a/tai", fake_run(stdout="7"))
        assert (ack.status, ack.note) == (s.PASS, "")

    def test_missing_reference_blocks_even_with_skip_reason(self):
        run = fake_run(1, stderr="HTTP 404")
        ack = s.acknowledge("docs: x tai#8\n[skip-sync] this one is ours", "a/tai", run)
        assert ack.status == s.BLOCK and "tai#8" in ack.note

    def test_unchecked_reference_passes_with_note(self):
        ack = s.acknowledge("docs: x tai#7", "a/tai", fake_run(raises=FileNotFoundError()))
        assert ack.status == s.PASS and "nie sprawdziłem tai#7" in ack.note

    def test_skip_with_reason_passes(self):
        assert s.acknowledge("docs: x\n\n[skip-sync] pricing is CRM only", "a/tai").status == s.PASS

    def test_bare_skip_blocks(self):
        ack = s.acknowledge("docs: x\n\n[skip-sync]", "a/tai")
        assert ack.status == s.BLOCK and "bez powodu" in ack.note

    def test_options_name_both_ways(self):
        text = s.options_text("a/tai")
        assert s.REF_EXAMPLE in text and s.SKIP_EXAMPLE in text and "a/tai" in text
