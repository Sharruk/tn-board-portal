# DOCUMENTATION_RULES.md — Documentation Rules
# TN Board Portal

> Documentation is part of the product. Never let it become outdated.

---

## Two Types of Documentation

### Private (`.ai/` folder)
AI operating manual. **Intentionally version-controlled** while the repository is private, so AI memory is shared across all development environments.
- For AI assistants and the developer's own memory
- Updated after every significant implementation
- Contains decisions, history, rules, and context
- **Never put API keys, passwords, tokens, or credentials here** — this folder is committed to Git

### Public (`/` + `docs/`)
Professional documentation visible to recruiters and contributors.
- Always in sync with the actual codebase
- Maintained to the same quality standard as the code

---

## When to Update Documentation

| Event | Update These |
|-------|-------------|
| New feature shipped | CHANGELOG.md, ROADMAP.md, docs/ARCHITECTURE.md |
| Bug fixed | CHANGELOG.md |
| Architecture changed | docs/ARCHITECTURE.md, ARCHITECTURE_RULES.md |
| New database table/RPC | DATABASE_RULES.md, docs/ARCHITECTURE.md |
| New migration applied | DATABASE_RULES.md (migration list) |
| New environment variable | README.md (env vars section), .env.example |
| New npm dependency | README.md (tech stack section if major) |
| Deployment changed | README.md (deployment section) |
| Roadmap item completed | ROADMAP.md |
| Architectural decision made | DECISIONS.md |

---

## Public Documentation Files

### `README.md`
The project's front page. Should cover:
- [ ] What the project does (problem statement)
- [ ] Live demo link
- [ ] Status badges (build, deployment, license)
- [ ] Feature list (student + admin)
- [ ] Architecture overview diagram
- [ ] Tech stack table
- [ ] Local installation steps
- [ ] Environment variable reference
- [ ] Supabase setup steps
- [ ] Vercel deployment guide
- [ ] Project structure tree
- [ ] Roadmap summary
- [ ] Contributing guide link
- [ ] License

### `CHANGELOG.md`
Format: [Keep a Changelog](https://keepachangelog.com) + [SemVer](https://semver.org)

```markdown
## [Unreleased]

### Added
- Feature name — brief description

### Fixed
- Bug description — what was wrong and how it was fixed

### Changed
- What changed and why

### Removed
- What was removed and why
```

**Every change that touches the user-visible product goes in CHANGELOG.md.**

### `ROADMAP.md`
- Current version features (live)
- Next version planned features
- Future version themes
- "Not planned" section
- Keep dates realistic — target quarters, not exact dates

### `CONTRIBUTING.md`
- Architecture constraints for contributors
- Local setup steps
- Build verification requirement
- Commit message format
- How to open issues

### `docs/ARCHITECTURE.md`
- High-level architecture diagram
- Folder structure (keep current)
- Database schema (all tables with columns)
- RLS policy table
- RPC function table
- Storage bucket table
- Request flow diagrams (search, upload, etc.)
- Technology choice rationale

---

## Documentation Quality Standards

- Write in clear English — no jargon, no abbreviations without explanation
- Use tables for structured data (tech stack, RLS policies, RPC functions)
- Use code blocks with syntax highlighting for all code examples
- Use ASCII diagrams for architecture (existing pattern in the project)
- Every section should stand alone — a reader should not need to read the whole file for context
- Remove outdated information immediately — outdated docs are worse than no docs

---

## What NOT to Document Publicly

- AI prompts or instructions (these go in `.ai/`)
- Implementation details that are obvious from reading the code
- Internal development notes
- Debugging sessions

---

## `.ai/` Documentation Files

| File | Update When |
|------|-------------|
| `AGENTS.md` | Workflow changes |
| `PROJECT_CONTEXT.md` | Roadmap changes, new modules shipped |
| `DEVELOPMENT_RULES.md` | Workflow improvements |
| `ARCHITECTURE_RULES.md` | Architecture changes |
| `DATABASE_RULES.md` | New migrations, schema changes |
| `CODING_STANDARDS.md` | New conventions established |
| `FEATURE_WORKFLOW.md` | Process improvements |
| `BUG_FIX_WORKFLOW.md` | New bug patterns discovered |
| `GIT_WORKFLOW.md` | Git process changes |
| `SECURITY_GUIDELINES.md` | New security patterns or vulnerabilities found |
| `PERFORMANCE_GUIDELINES.md` | New performance patterns or benchmarks |
| `RESUME_GOALS.md` | New features worth highlighting |
| `DECISIONS.md` | Every significant architectural decision |
| `CHANGE_HISTORY.md` | Every implementation session |
| `PROMPTS.md` | Useful AI prompts worth saving |
