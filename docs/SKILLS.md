# Skills Catalog

All Claude Code skills available in this template.
Invoke a skill with `/skill-name` in the conversation.

## Vendored (external sources)

| Skill | Source | Description |
|-------|--------|-------------|
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Design intelligence: 50+ styles, 161 palettes, 57 font pairings, 99 UX guidelines across 10 stacks |
| `security` | [agamm/claude-code-owasp](https://github.com/agamm/claude-code-owasp) | OWASP Top 10:2025, ASVS 5.0, LLM Top 10 — security review and threat modeling |
| `a11y` | [fecarrico/A11Y.md](https://github.com/fecarrico/A11Y.md) | Accessibility audit (WCAG 2.2 AA): keyboard nav, screen reader, contrast, ARIA |
| `perf` | [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) | Web performance: Core Web Vitals (LCP/INP/CLS), budgets, Lighthouse optimization |
| `review` | [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill) | Code review for 15+ languages: React, Vue, Go, Python, Rust, TypeScript and more |

## Custom

| Skill | Description |
|-------|-------------|
| `git` | Git workflow: branch strategy, commit format (Conventional Commits), PR protocol, conflict resolution |
| `new-project-scope` | Project intake wizard — 6 questions → `docs/PROJECT_SCOPE.md` + `ADR-001` |
| `adr` | Architecture Decision Record generator — interview → `docs/adr/ADR-NNN.md` |
| `api` | REST API design review: naming, HTTP methods, status codes, errors, pagination, versioning |
| `debug` | Systematic debugging protocol: reproduce → isolate → hypothesize → verify → fix |
| `deploy` | Pre-deployment checklist: code, env, database, infra, rollback, post-deploy |
| `retro` | Sprint/project retrospective — 5 questions → structured retro + action items to `docs/TASKS.md` |

## Plugins (install separately, per developer)

Plugins bundle an MCP server + skills in one install. They are **not** vendored into the repo —
each developer installs them once on their machine. The AI will suggest the relevant plugin
when it detects you're working in that context.

| Plugin | Install | When to use |
|--------|---------|-------------|
| **Figma** | `claude plugin install figma@claude-plugins-official` | Working with Figma files — reading components/tokens, generating code from frames, pushing designs back to Figma, Code Connect, FigJam diagrams |

### Figma plugin — what you get

After `claude plugin install figma@claude-plugins-official` and authenticating:

- **MCP tools** — Claude can read/write your Figma files (`use_figma`, `create_new_file`, `generate_diagram`)
- **8 built-in skills** — loaded automatically when needed:
  - `/figma-use` — prerequisite for any write action in Figma
  - `/figma-generate-design` — app page / view → Figma frames using your design system tokens
  - `/figma-generate-library` — build a full design system in Figma from codebase
  - `/figma-code-connect` — map Figma components ↔ code (`.figma.ts` / `.figma.js`)
  - `/figma-generate-diagram` — flowcharts, ERD, architecture diagrams in FigJam
  - `/figma-create-new-file`, `/figma-use-figjam`, `/figma-use-slides`

Source: [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide) · [Figma docs](https://help.figma.com/hc/en-us/articles/39888612464151)

## Management

```bash
# Check for updates (dry-run)
python3 scripts/update-skills.py

# Apply safe updates
python3 scripts/update-skills.py --apply

# Validate SKILL.md frontmatter
python3 scripts/validate-skills.py

# Update single skill
python3 scripts/update-skills.py --skill security
```
