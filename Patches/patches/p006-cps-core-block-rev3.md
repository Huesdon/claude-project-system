# p006 — CLAUDE.md cps-core block → rev 3

**ID:** `p006-cps-core-block-rev3`
**Profile:** Both (Core and Full)
**CPS version introduced:** Phase 8.7 (2026-04-09 — Input/Output Folders section added)

Detection checks are in `patch-index.md`. This file contains only the actions.

---

## Actions (apply in order)

### Action a — Upgrade or insert cps-core block in CLAUDE.md

Skip if both detection checks pass (CLAUDE.md exists AND contains `<!-- cps-core BEGIN rev: 3 -->`).

If CLAUDE.md contains a `<!-- cps-core BEGIN rev: 1 -->` or `<!-- cps-core BEGIN rev: 2 -->` ... `<!-- cps-core END -->` block: replace the entire block (from BEGIN to END inclusive) with the new rev 3 block below.

If CLAUDE.md has no cps-core block at all: append the block below at the end of the file (preceded by a blank line if the file does not end with one).

Replace/insert with this exact content:

```
<!-- cps-core BEGIN rev: 3 -->
<!-- Managed by cps-scaffold.ps1 — do not edit between BEGIN/END markers; re-run the script to update. -->

## Delegation

Tier 1–4 mechanical tasks (file writes, mutations, formatting, transforms) delegate to Haiku. Sonnet handles architecture and decisions. See user preferences for the full routing heuristic.

---

## Session Startup

On session open: surface top 1–3 active tasks (§9 RECOMMEND) before any other work. Load memory if available. Do not scope-clarify vague openers when a task backlog exists.

---

## Document Access Hierarchy

1. This CLAUDE.md (always loaded)
2. `_TOC.md` companions (for any Reference/ or Documentation/md/ doc >200 lines)
3. Targeted section reads with `offset`/`limit`
4. Full doc reads — last resort only

---

## Documentation

- `Reference/` — canonical design docs, patterns, decisions, lessons
- `Documentation/md/` — user-facing markdown docs

---

## Input / Output Folders

- `Input/` — drop source materials here for Claude to pick up and analyze. Markdown files in `Input/` are indexed by CPS (Full profile) via `Input/**/*.md` in `source_paths`.
- `Output/` — **default drop zone for all Claude-generated deliverables** (reports, exports, presentations, one-off artifacts) that don't belong in `Documentation/` or `Reference/`. Claude writes deliverables here unless directed elsewhere.

---

## 9. Task Module — Trigger Summary

Session-start RECOMMEND, tier-based backlog, single source of truth in `Reference/Claude/tasks.json`.
Full spec: `Reference/Claude/CPS_Task_Module.md`. Owned by the `task` skill.

---

## 11. TOC Maintenance Rule

Any `Reference/` or `Documentation/md/` file over 200 lines requires a companion `[SourceFilename]_TOC.md` in the same directory.
Full spec: `Reference/Claude/CPS_TOC_Rule.md`.

---

## 12. Knowledge Capture — Taxonomy

Five buckets under `Reference/`: Patterns, Decisions, Lessons, Ideas (low-friction, promote when ready), Roadmap (committed intentions with Now/Next/Later horizon). Self-trigger gate requires all four capture criteria (Ideas have a lower bar — "what if" thoughts welcome). Promotion flow: Idea→Roadmap→Tasks.
Full spec: `Reference/Claude/CPS_Capture_Taxonomy.md`.
Trigger phrases: "add idea", "add to roadmap", "promote [title] to roadmap", "promote [title] to tasks".

<!-- cps-core END -->
```
