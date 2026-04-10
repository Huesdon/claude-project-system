# p002 — Documentation Scaffold

**ID:** `p002-documentation-scaffold`
**Profile:** Both (Core and Full)
**CPS version introduced:** CPS_Design.md rev 4 (2026-04-09)

Detection checks are in `patch-index.md`. This file contains only the actions.

---

## Actions (apply in order)

### Action a — Create `Documentation/` and `Documentation/md/`

Skip if both directories already exist.

Create `Documentation/` (if missing), then create `Documentation/md/` (if missing). Both are empty placeholders — no files are written inside them.

Report: **CREATED** for each directory created, **SKIPPED** if already present.
