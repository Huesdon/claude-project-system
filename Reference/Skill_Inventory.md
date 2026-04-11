# CPS Skill Inventory

> **Last Updated:** 2026-04-11 (patcher retirement — `cps-patcher` row removed; upgrade model covered by `cps-init` + `cps-setup` per `Reference/Decisions/2026-04-11-cps-upgrade-model-two-entry-points.md`)
> **Scope:** Active CPS skills installed globally in `/mnt/.claude/skills/` on this dev machine. Local inventory — not a distribution manifest.

## Retired

- **`cps-patcher`** — retired 2026-04-11. Duplicated `cps_scaffold.py` logic. Scaffold drift now handled by re-running `cps-init`. Rationale: `Reference/Decisions/2026-04-11-cps-upgrade-model-two-entry-points.md`. Installed `/mnt/.claude/skills/cps-patcher/` directory must be deleted by hand (read-only mount blocks MCP delete).

The `File` column points at a workspace `.skill` staging bundle when one exists.

**Canonical source tree:** `Skills/src/<name>/` is the edit target for every skill that has a local workspace bundle. `.skill` files under `Skills/` are built artifacts — never edit them directly, and never edit files under `/mnt/.claude/skills/` (read-only per global CLAUDE.md §0a). Rebundle via `python Skills/tools/rebundle.py [names...]` (see Tooling below), then hand-install the updated `.skill` through `mcp__cowork__present_files`.

| Skill | File | Trigger phrases | Status |
|-------|------|-----------------|--------|
| `cps-setup` | `Skills/cps-setup.skill` | "install cps", "set up cps", "deploy cps", "bootstrap cps", "install cps core", "install cps full", "upgrade cps to full" | **Canonical** (rev 10 — solo-developer, menu-driven Core or Full installer; bundle ships 5 runtime `.py` files + SKILL.md only, no sub-skills). Rev 11 wording pass + bundle repair tracked as follow-up task. |
| `cps-init` | `Skills/cps-init.skill` | "cps-init", "scaffold cps", "initialize cps project" | Active (rev 3 — fetches `cps_scaffold.py` from GitHub main at runtime; no bundled scripts) |
| `cps-query` | `Skills/cps-query.skill` | "cps query [question]", "search knowledge base" | Active |
| `cps-refresh` | `Skills/cps-refresh.skill` | "refresh cps", "reindex" | Active |
| `cps-capture` | `Skills/cps-capture.skill` | "save this pattern", "lesson learned", "worth remembering", "capture this", "cps-capture" | Active |
| `task` | `Skills/task.skill` | "add a task", "mark that done", "task backlog", "show me open tasks" | Active |

## Maintenance

Update this file when:

- Adding a new CPS skill (new row + version + trigger phrases)
- Retiring a skill (move to an "Archived" section at the bottom)
- Revving an existing skill (update rev number in Status column)
- Changing trigger phrases (update the Trigger phrases column)

Rebundle via `python Skills/tools/rebundle.py <name>` and reinstall via `mcp__cowork__present_files` after any source change.

## Tooling

| Tool | Path | Purpose |
|------|------|---------|
| `rebundle.py` | `Skills/tools/rebundle.py` | Zips `Skills/src/<name>/` → `Skills/<name>.skill`. Run with no args to rebuild every skill; pass names to target. `--list` enumerates available sources. Atomic write via `.tmp` rename. |

## Source Tree Convention

- `Skills/src/<name>/SKILL.md` — canonical edit target.
- `Skills/<name>.skill` — built artifact produced by `rebundle.py`. Ignored by hand-edit; regenerate on every source change.
- `/mnt/.claude/skills/<name>/` — installed location (read-only). Updated only by reinstalling a freshly built `.skill` via `mcp__cowork__present_files`.

Workflow: edit `Skills/src/<name>/SKILL.md` → `python Skills/tools/rebundle.py <name>` → deliver the resulting `.skill` via `mcp__cowork__present_files` to reinstall.
