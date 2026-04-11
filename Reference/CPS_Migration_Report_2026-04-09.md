# CPS Migration Report — 2026-04-09

**Source:** `H:\Claude Cowork\Projects\CPS` (CPS dev project, archived)
**Target:** `H:\Claude Cowork\Projects\Claude Project System` (new CPS Full install, now canonical dev home)
**Executed:** 2026-04-09

> **2026-04-10 update:** `cps-scaffold.cmd`, `cps-scaffold.ps1`, and `check_scaffold_parity.py` have since been retired (cps-init now fetches `cps_scaffold.py` from GitHub raw at runtime). References below are preserved as historical record.

---

## Files Migrated (46 total)

| Category | Count | Notes |
|----------|-------|-------|
| Runtime/ | 7 | cps_server.py, cps_chunker.py, cps_embedder.py, cps_graph.py, cps_test_suite.py, cps_config.json, README.md |
| Skills/ | 8 | 6 .skill bundles + zingWxv6 scratch dir |
| Documentation/md/ | 2 | CPS_Setup_Guide.md, CPS_Troubleshooting_Guide.md |
| Reference/ (top-level) | 13 | 11 .md files + cps-scaffold.cmd + cps-scaffold.ps1 |
| Reference/Patterns/ | 3 | 2 captures + _INDEX.md (stale .tmp excluded) |
| Reference/Decisions/ | 5 | 4 captures + _INDEX.md |
| Reference/Lessons/ | 1 | _INDEX.md only |
| Reference/Claude/ | 4 | tasks.json, tasks_backlog.json, tasks_completed.log, Instruction_Architecture.md |
| Root scratch | 1 | cps-c-scratch.txt |
| CLAUDE.md | 1 | Merged (Phase C) — not a raw copy |

---

## Files Not Migrated

- `Reference/wip-archive/` — dropped by user decision (stale redesign work)
- `Output/` — dropped by user decision (build artifacts only)
- `__pycache__/` (6 items) — auto-generated, excluded
- `Reference/Patterns/_INDEX.md.tmp.18077.*` — stale tempfile, excluded and subsequently deleted from target

---

## Phase A — Conflict Resolutions

Three files were pre-seeded by cps-setup in the target but had drifted from dev versions. Dev won on all three:

- `Reference/CPS_Capture_Taxonomy.md` — dev overwrote target seed
- `Reference/CPS_TOC_Rule.md` — dev overwrote target seed
- `Reference/CPS_Task_Module.md` — dev overwrote target seed
- `Reference/cps-scaffold.cmd` — matched, no action
- `Reference/cps-scaffold.ps1` — matched, no action

---

## Phase C.1 — Spec Propagations

Two items were present in dev CLAUDE.md inline §9/§12 but absent from spec files. Propagated before migration:

1. **CPS_Task_Module.md** — two changes:
   - Added AskUserQuestion "Confirmed complete / Reopen it" gate to §3 (immediate completion gate was missing from spec)
   - Corrected reprioritization threshold: spec said 5, CLAUDE.md said 10 — resolved to 10 (CLAUDE.md canonical)

2. **CPS_Capture_Taxonomy.md** — added Pre-design retrieval (read trigger) section (was in dev CLAUDE.md §12 but absent from spec)

3. **CPS_TOC_Rule.md** — no changes needed (no drift)

---

## Phase C — CLAUDE.md Merge

Strategy: init version (cps-setup-generated, 60 lines) as base; dev content back-populated after the managed cps-core block.

- `<!-- cps-core BEGIN/END -->` managed block preserved intact (Delegation, Session Startup, Document Access Hierarchy, Documentation, Input/Output, §9/§11/§12 pointer-style)
- §9 / §11 / §12: kept as lean pointers to Reference spec files (init wins — externalization pattern)
- Back-populated from dev: §0 House Rules, §1 Project Identity, §2 What CPS Does, §3 Runtime Files (self-hosting sync), §4 Skills table, §5 Single-Tenant Architecture, §6 Phase History, §7 Documentation table (TOC registry), §8 CPS Usage — On-Demand CLI, §10 Deployment Checklist
- Rev reset to: **rev 1 (2026-04-09 — migrated from CPS dev project)**
- Final size: ~150 lines

---

## Phase D — Structural Validation (In-Session)

All pass:

- Runtime/ — 7 files present; .py filenames match .cps/ (self-sync will fire on next ingest)
- Skills/ — all 6 .skill bundles present
- Reference/ — 11 .md + TOC + scaffold scripts present
- CPS_Integration_Spec_TOC.md — present (§11 compliance maintained)
- Reference/Claude/ — tasks.json + backlog + completed log + Instruction_Architecture all present
- Patterns/ stale .tmp removed

---

## Pending Validation (Run in new project session)

Run these in order in the first session opened in the new project:

1. `cps-refresh` — triggers Runtime/ → .cps/ self-sync and incremental reindex
2. `cps purge` then full `cps-ingest` — rebuild cps.db against all migrated docs
3. `cps_graph_build`
4. `python .cps/cps_test_suite.py`
5. `task RECOMMEND` — verify tasks.json loads and surfaces top T1/T2
6. `cps-query "what does the task module trigger on session start"` — spot-check retrieval

---

## Recommendations

- Rename source project folder to `CPS-archive-20260409` to prevent accidental edits
- The source project's `.cps/` db is now stale and should not be queried going forward
- All future CPS dev work starts from `H:\Claude Cowork\Projects\Claude Project System`
