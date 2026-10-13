#!/usr/bin/env python3
"""Tell the commit guards which stack the project uses.

Run by the scope wizard (skill new-project-scope) once the stack is decided, or by hand:

  python3 scripts/set-stack.py laravel     # set
  python3 scripts/set-stack.py --list      # show the table

Writes into .claude/hooks/config.json:
  - stack         the chosen name, so the guided start can check that the stack was set
  - src_dirs      where the application code lives — guard-tests-with-src checks only these
  - adr_patterns  the chosen platform's group is switched on; the groups of the other
                  platforms stay inactive in _adr_patterns_optional

Safe to run again with another stack: the previously enabled platform group is switched off.
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / ".claude" / "hooks" / "config.json"

DEFAULT_STACK = "inny"
STACK_PRESETS: dict[str, dict] = {
    "node": {"label": "Node (Next.js, React, TypeScript)", "src_dirs": ["src"], "adr_group": None},
    "laravel": {"label": "Laravel", "src_dirs": ["app"], "adr_group": None},
    "symfony": {"label": "Symfony", "src_dirs": ["src"], "adr_group": None},
    "wordpress": {"label": "WordPress", "src_dirs": ["wp-content/themes", "wp-content/plugins"],
                  "adr_group": "WordPress"},
    "prestashop": {"label": "PrestaShop", "src_dirs": ["modules", "override"], "adr_group": "PrestaShop"},
    "magento": {"label": "Magento", "src_dirs": ["app/code"], "adr_group": "Magento"},
    "python": {"label": "Python", "src_dirs": ["src"], "adr_group": None},
    "go": {"label": "Go", "src_dirs": ["cmd", "internal", "pkg"], "adr_group": None},
    "rails": {"label": "Ruby on Rails", "src_dirs": ["app", "lib"], "adr_group": None},
    DEFAULT_STACK: {"label": "inny / jeszcze nie wiem", "src_dirs": ["src"], "adr_group": None},
}


def apply_stack(config: dict, stack: str) -> dict:
    """Return config with src_dirs and the platform ADR group set for `stack`.

    The groups in _adr_patterns_optional are a catalogue and are never removed from it;
    adr_patterns holds the project's own patterns plus a copy of at most one group.
    """
    preset = STACK_PRESETS[stack]
    # the name is recorded so project-setup.py can tell "stack set" from "defaults untouched"
    # (several stacks use the same directories as the default)
    config["stack"] = stack
    config["src_dirs"] = list(preset["src_dirs"])

    optional = config.get("_adr_patterns_optional")
    if not isinstance(optional, dict):
        return config
    platform_entries = [entry for group in optional.values() for entry in group]
    kept = [entry for entry in config.get("adr_patterns", []) if entry not in platform_entries]
    config["adr_patterns"] = kept + list(optional.get(preset["adr_group"], []))
    return config


def format_table() -> str:
    lines = []
    for name, preset in STACK_PRESETS.items():
        group = f"  + wzorce ADR: {preset['adr_group']}" if preset["adr_group"] else ""
        lines.append(f"  {name:<11} {preset['label']:<34} kod: {', '.join(preset['src_dirs'])}{group}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set the project's stack for the commit guards (code directories, ADR patterns).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Stacks:\n" + format_table(),
    )
    parser.add_argument("stack", nargs="?", choices=list(STACK_PRESETS), metavar="STACK",
                        help="one of: " + ", ".join(STACK_PRESETS))
    parser.add_argument("--list", action="store_true", help="print the table of stacks and exit")
    args = parser.parse_args(argv)

    if args.list:
        print(format_table())
        return 0
    if not args.stack:
        parser.error("podaj stos (albo --list)")

    if not CONFIG_PATH.is_file():
        print(f"❌ Brak {CONFIG_PATH.relative_to(ROOT)} — skopiuj go z config.json.example "
              "(docs/GUARDS.md, sekcja „Konfiguracja strażników”).", file=sys.stderr)
        return 1
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        print(f"❌ {CONFIG_PATH.relative_to(ROOT)} nie jest poprawnym JSON-em: {err}", file=sys.stderr)
        return 1
    if not isinstance(config, dict):
        print(f"❌ {CONFIG_PATH.relative_to(ROOT)} nie zawiera obiektu konfiguracji.", file=sys.stderr)
        return 1

    apply_stack(config, args.stack)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    preset = STACK_PRESETS[args.stack]
    print(f"✓ Stos: {args.stack} ({preset['label']})")
    print(f"  katalogi kodu (src_dirs): {', '.join(preset['src_dirs'])}")
    print(f"  wzorce ADR platformy: {preset['adr_group'] or 'żadne (tylko ogólne)'}")
    print(f"  zapisano: {CONFIG_PATH.relative_to(ROOT)} — plik jest wspólny, zacommituj go")
    return 0


if __name__ == "__main__":
    sys.exit(main())
