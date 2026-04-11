# Patch p007: Content Routing Table (cps-core rev 4)

**Applies to:** Core + Full
**Date added:** 2026-04-11

## Detection

Patch is PRESENT (skip) if ALL of the following are true:
- `CLAUDE.md` exists
- `CLAUDE.md` contains the string `### Content Routing`

If ANY check fails → patch is NEEDED.

## Actions

### 1. Inject Content Routing subsection into `CLAUDE.md`

Locate the `## Document Access Hierarchy` section inside the `<!-- cps-core BEGIN -->` block. Insert the block below immediately after the numbered list item `4. Full doc reads — last resort only` and before the next `---` separator.

Write verbatim:

```markdown

### Content Routing

Read the mapped file. Create it as an empty stub if missing.

| Topic | File |
|---|---|
| API conventions | `reference/api-standards.md` |
| Testing guidelines | `reference/testing.md` |
| Deployment rules | `reference/deploy.md` |
```

### 2. Bump cps-core block rev marker

Replace `<!-- cps-core BEGIN rev: 3 -->` with `<!-- cps-core BEGIN rev: 4 -->` in `CLAUDE.md`.
