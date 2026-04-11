# Patch p006: CLAUDE.md §0 House Rules Block (rev3)

**Applies to:** Core + Full
**Date added:** 2026-04-10

## Detection

Patch is PRESENT (skip) if ALL of the following are true:
- `CLAUDE.md` exists
- `CLAUDE.md` contains the marker `<!-- CPS:HOUSE-RULES-v3 -->`

If ANY check fails → patch is NEEDED.

## Actions

### 1. Inject §0 House Rules block into `CLAUDE.md`

If `CLAUDE.md` already contains a `## 0. House Rules` section bounded by older CPS markers, replace the entire block. Otherwise, insert immediately before the first `## 1.` section heading.

Write the block verbatim:

```markdown
<!-- CPS:HOUSE-RULES-v3 -->
## 0. House Rules

These rules apply to every action taken in this project.

- **Permission first.** Always ask for explicit user approval before creating or modifying any file. No exceptions for "small" edits.
- **Skills folder is read-only.** `/mnt/.claude/skills/` cannot be written to directly. Build new or updated skills in a temp directory, zip as `.skill`, and present via `mcp__cowork__present_files`.
- **Token discipline.** Read the smallest, most targeted file first. CPS query before raw file read. `_TOC.md` companion before any full doc read.
<!-- /CPS:HOUSE-RULES-v3 -->
```
