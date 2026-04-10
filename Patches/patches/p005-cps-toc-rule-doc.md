# p005 — Canonical Reference Docs: CPS_TOC_Rule.md

**ID:** `p005-cps-toc-rule-doc`
**Profile:** Both (Core and Full)
**CPS version introduced:** Phase 8.7 (2026-04-08 externalization)

Detection checks are in `patch-index.md`. This file contains only the actions.

---

## Actions (apply in order)

### Action a — Create `Reference/Claude/CPS_TOC_Rule.md`

Skip if both detection checks pass (file exists AND contains `<!-- rev: 1 -->`).

Write the file with this exact content:

```
<!-- rev: 1 -->
# CPS TOC Maintenance Rule (MANDATORY)

> Externalized from CLAUDE.md §11 on 2026-04-08 to reduce per-session token cost. CLAUDE.md retains a one-line summary pointing at this file.

Every `Reference/` or `Documentation/md/` file that exceeds **200 lines** must have a companion `_TOC.md` file. The TOC lists every `##` and `###` heading with its line number in a two-column markdown table (`Line | Section`). This enables targeted `offset`/`limit` reads instead of loading full documents and is the mechanism that lets the §7 read hierarchy actually work.

## When to Create a TOC

- Delegation: Use Haiku (Tier 1) to generate TOC tables from finished files.
- Any new `Reference/` or `Documentation/md/` file that is written above 200 lines, or any existing file that grows past 200 lines during edits.
- Immediately — not deferred to a cleanup pass.
- Created in the same session as the doc itself; do not close a session with an over-threshold doc that lacks a TOC.

## TOC File Naming and Location

- Same directory as the source file.
- Name: `[SourceFilename]_TOC.md` (e.g. `CPS_Integration_Spec_TOC.md`).
- Format: a two-column markdown table with header `| Line | Section |`, one row per `##` or `###` heading, line numbers absolute.

## After Adding or Removing a TOC

1. Update the corresponding row in the CLAUDE.md §7 doc table (Lines column + TOC column).
2. Update the TOC count line directly under the table ("TOC count: N docs").
3. Run `cps-refresh` so the new TOC is indexed and discoverable to query callers.

## Authoritative Registry

The CLAUDE.md §7 doc table is the single source of truth for TOC coverage. If a doc is over threshold and the TOC column is empty, the project is out of compliance and should be fixed before any new doc work begins. Do not rely on filesystem scans — the table is the canonical answer.

## Exemption — CLAUDE.md Files

CLAUDE.md is always fully loaded at session start, so a TOC produces no token savings for the file itself. CLAUDE.md files are exempt from the 200-line TOC threshold. Apply normal session-hygiene pressure instead: keep CLAUDE.md tight by folding stale phase history, retiring dead sections, and pushing rationale into Reference/*.md files.
```
