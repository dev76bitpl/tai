# Katalog skillów

Wszystkie skille Claude Code dostępne w tym template.

Skill ładuje się gdy Claude wykryje odpowiednie słowo kluczowe. Każdy skill ma jeden **kanoniczny trigger** —
krótkie słowo które wpisujesz świadomie. Nie używaj składni `/command` (to dla wbudowanych komend Claude Code).

## Szybka ściągawka — wpisz to żeby wywołać skill

| Wpisz | Skill | Co robi |
|-------|-------|---------|
| `scope` | new-project-scope | Wywiad 6 pytań → `PROJECT_SCOPE.md` + `ADR-001` |
| `debug` | debug | Protokół debugowania krok po kroku |
| `deploy` | deploy | Checklist przed wdrożeniem |
| `retro` | retro | Retrospektywa → action items |
| `adr` | adr | Generator ADR → `docs/adr/ADR-NNN.md` |
| `api design` | api | Przegląd projektu REST API |
| `git` | git | Branch strategy, commit format, PR |
| `security review` | security | OWASP Top 10, ASVS 5.0 |
| `a11y` | a11y | Audit dostępności WCAG 2.2 AA |
| `perf` | perf | Core Web Vitals, Lighthouse |
| `review` | review | Code review PR |
| `ui design` | ui-ux-pro-max | Design intelligence |

## Skille zewnętrzne (vendored)

| Skill | Źródło | Opis |
|-------|--------|------|
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Design intelligence: 50+ stylów, 161 palet, 57 zestawień fontów, 99 wytycznych UX na 10 stackach |
| `security` | [agamm/claude-code-owasp](https://github.com/agamm/claude-code-owasp) | OWASP Top 10:2025, ASVS 5.0, LLM Top 10 — przegląd bezpieczeństwa i threat modeling |
| `a11y` | [fecarrico/A11Y.md](https://github.com/fecarrico/A11Y.md) | Audit dostępności (WCAG 2.2 AA): nawigacja klawiaturą, screen reader, kontrast, ARIA |
| `perf` | [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) | Wydajność web: Core Web Vitals (LCP/INP/CLS), budżety, optymalizacja Lighthouse |
| `review` | [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill) | Code review dla 15+ języków: React, Vue, Go, Python, Rust, TypeScript i innych |

## Skille własne

| Skill | Trigger | Opis |
|-------|---------|------|
| `new-project-scope` | `scope` | Wizard projektu — 6 pytań → `docs/PROJECT_SCOPE.md` + `ADR-001` |
| `git` | `git` | Workflow git: strategia branchy, format commita (Conventional Commits), protokół PR |
| `adr` | `adr` | Generator ADR — wywiad → `docs/adr/ADR-NNN.md` |
| `api` | `api design` | Przegląd projektu REST API: nazewnictwo, metody HTTP, kody statusu, paginacja |
| `debug` | `debug` | Protokół debugowania: odtwórz → wyizoluj → hipoteza → zweryfikuj → napraw |
| `deploy` | `deploy` | Checklist przed wdrożeniem: kod, env, baza, infrastruktura, rollback, post-deploy |
| `retro` | `retro` | Retrospektywa sprintu/projektu — 5 pytań → podsumowanie + action items do `TASKS.md` |

## Pluginy (instalowane per developer, poza repo)

Plugin bundluje MCP server + skille w jednej instalacji. Nie trafia do repo —
każdy developer instaluje raz na swojej maszynie. AI podpowie o pluginie gdy wykryje pasujący kontekst.

| Plugin | Instalacja | Kiedy używać |
|--------|-----------|--------------|
| **Figma** | `claude plugin install figma@claude-plugins-official` | Praca z plikami Figma — odczyt komponentów/tokenów, generowanie kodu z framek, zapis do Figma, Code Connect, diagramy FigJam |

### Figma plugin — co dostajesz

Po `claude plugin install figma@claude-plugins-official` i uwierzytelnieniu:

- **Narzędzia MCP** — Claude może czytać/pisać pliki Figma (`use_figma`, `create_new_file`, `generate_diagram`)
- **8 wbudowanych skillów** — ładowane automatycznie gdy potrzebne:
  - `figma-use` — wymagany przed każdą akcją zapisu w Figma
  - `figma-generate-design` — strona/widok aplikacji → framki Figma z tokenami design systemu
  - `figma-generate-library` — buduje pełny design system w Figma z codebase
  - `figma-code-connect` — mapuje komponenty Figma ↔ kod (`.figma.ts` / `.figma.js`)
  - `figma-generate-diagram` — flowcharty, ERD, diagramy architektury w FigJam
  - `figma-create-new-file`, `figma-use-figjam`, `figma-use-slides`

Źródło: [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide) · [Dokumentacja Figma](https://help.figma.com/hc/en-us/articles/39888612464151)

## Zarządzanie skillami

```bash
# Sprawdź aktualizacje (dry-run)
python3 scripts/update-skills.py

# Zastosuj bezpieczne aktualizacje
python3 scripts/update-skills.py --apply

# Waliduj frontmatter SKILL.md
python3 scripts/validate-skills.py

# Zaktualizuj jeden skill
python3 scripts/update-skills.py --skill security
```
