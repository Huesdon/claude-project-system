# p003 — Input/Output Convenience Directories

**ID:** `p003-input-output-dirs`
**Profile:** Both (Core and Full)
**CPS version introduced:** cps-scaffold.ps1 (2026-04-09)

Detection checks are in `patch-index.md`. This file contains only the actions.

---

## Actions (apply in order)

### Action a — Create `Input/` and `Output/`

Skip if both directories already exist.

Create `Input/` (if missing), then `Output/` (if missing). Both are empty — no stub files are written.

For Full profile only: after creating `Input/`, check `.cps/cps_config.json`. If `source_paths` does not contain `"Input/**/*.md"`, add it. Preserve all other config fields.

Report: **CREATED** for each directory created, **SKIPPED** if already present.
