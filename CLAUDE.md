# CLAUDE.md

> **Last Updated:** 2026-04-10 (rev 9 — §0 rules rewritten for direct GitHub MCP access; gh_pull.py and gitpush.bat retired)
> **Status:** Single-tenant dev home. CPS Phase 8.7.

<!-- cps-core BEGIN rev: 2 -->
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

---

## 0. House Rules (inherited from global CLAUDE.md)

These rules apply to every action taken in this project.

- **Permission first.** Always ask for explicit user approval before creating or modifying any file. No exceptions for "small" edits.
- **Skills folder is read-only.** `/mnt/.claude/skills/` cannot be written to directly. Build new or updated skills in a temp directory, zip as `.skill`, and present via `mcp__cowork__present_files`.
- **Token discipline.** Read the smallest, most targeted file first. CPS query before raw file read. `_TOC.md` companion before any full doc read. See global CLAUDE.md for the full hierarchy.
- **Rebundle on Runtime/ edit.** Any session that edits a `Runtime/*.py` file MUST rebundle `cps-setup.skill` before close. Drift between the live `Runtime/` source and the bundled `.py` files inside `Skills/cps-setup.skill` causes silent install failures in downstream projects.
- **GitHub repo I/O uses the MCP github connector.** During CPS dev sessions, Claude reads, writes, and pushes directly via `mcp__github__get_file_contents`, `mcp__github__create_or_update_file`, `mcp__github__push_files`, and `mcp__github__list_commits` against `Huesdon/claude-project-system`. No subprocess git, no `.bat` helpers, no manual push step. The mount-corruption rule still applies to any local git operation — there should be no reason to run one.
- **Push scaffold edits to GitHub main.** Any session that edits `Reference/cps_scaffold.py` MUST push the change to `main` via `mcp__github__create_or_update_file` before close. `cps-init` (rev 3+) fetches `cps_scaffold.py` from `raw.githubusercontent.com/Huesdon/claude-project-system/main/Reference/cps_scaffold.py` at runtime — **no skill rebundle required**. Unpushed scaffold edits will not reach downstream projects. The template strings in `cps_scaffold.py` and `cps-scaffold.ps1` must still stay in sync — edits to one require the matching edit to the other — because `.ps1` is the manual Windows fallback users download directly from the repo.
- **Truncation.** Cowork can falsely report files as shorter than they are. Never flag apparent truncation as a problem unprompted. If content seems missing and verification matters before acting, call `mcp__github__get_file_contents` against `Huesdon/claude-project-system` to pull the authoritative copy from `main` and diff against local — that is the ground truth.
- **Patch catalog entry on new patchable feature.** Any session that adds a **structurally new** scaffolded artifact (new dirs, new stub files, new CLAUDE.md section blocks, new config keys) MUST add a corresponding entry to `Patches/patch-index.md` (detection block + table row + updated sentinel) AND a new per-patch file under `Patches/patches/`, then push the whole change atomically to `main` via `mcp__github__push_files`. **No skill rebundle required** — the patcher WebFetches the catalog from GitHub at runtime. **Does NOT apply to:** bugfixes that correct existing template content, rev variable corrections, or skill rewrites that don't change what gets deployed to downstream projects.

---

## 1. Project Identity

- **System:** Claude Project System (CPS) — a context engine with four modules (Knowledge, Tasks, Docs, Sessions) that runs a Cowork project's long-term operating discipline
- **Developer:** Shane Huesdon @ Glidefast Consulting
- **Stack:** Python (on-demand subprocess, MCP/stdio transport), SQLite (sqlite-vec), ONNX (all-MiniLM-L6-v2), Claude Cowork skills
- **Runtime location:** `Runtime/` — canonical source of truth for all Python files
- **Skills location:** `Skills/` — installable `.skill` files for Cowork projects

---

## 2. What CPS Is

CPS is a **context engine** with **four modules** that together run a Cowork project's long-term operating discipline. One system, one source of truth per project, invoked on demand — not a background process.

**The Engine (core).** A local semantic index (SQLite + sqlite-vec + ONNX `all-MiniLM-L6-v2`) that ingests project markdown and JSON, answers cited queries in ~1K tokens instead of 3K–12K tokens of raw file reads, and runs via subprocess CLI — no background process, no `.mcp.json` registration required.

**Core loop (Full profile):** ingest → chunk → embed → store → serve queries.

**MCP tools:** `cps_search`, `cps_retrieve`, `cps_status`, `cps_ingest`, `cps_prime`, `cps_purge`, `cps_graph_build`, `cps_graph_query`. Full descriptions available via `cps_status` or `Runtime/README.md`.

### The Four Modules

1. **Knowledge Management** — Three-bucket taxonomy (Patterns / Decisions / Lessons) under `Reference/`. Write via `cps-capture`, search via `cps-query`, re-index via `cps-refresh`. Full spec: §12 → `Reference/Claude/CPS_Capture_Taxonomy.md`.
2. **Task Management** — Tiered backlog with a single source of truth in `Reference/Claude/tasks.json`, surfaced at session open via §9 RECOMMEND, managed by the `task` skill. Full spec: §9 → `Reference/Claude/CPS_Task_Module.md`.
3. **Documentation Management** — Canonical markdown single-source-of-truth under `Documentation/md/` and `Reference/`, enforced by the 200-line TOC companion rule. Full spec: §11 → `Reference/Claude/CPS_TOC_Rule.md`.
4. **Session & Token Management** — Document Access Hierarchy (CLAUDE.md → `_TOC.md` → targeted read → full read), session hygiene (one workstream per session, ~15-exchange close suggestion, summary-on-fill), and Haiku delegation for tier 1–4 mechanical work. Enforced by the Delegation note and §0 House Rules at the top of this file.

### Profiles

CPS ships in two profiles. Full is a strict superset of Core; graduation is additive (no migration).

- **Core** — Scaffold + three pillars. Skills: `cps-init`, `task`, `cps-capture`. Retrieval is grep over `Reference/` and `Documentation/md/`, guided by the TOC rule. No `.cps/`, no Python runtime, no `.mcp.json`.
- **Full** — Core + Python runtime (`Runtime/`, `.cps/`) + `cps-query` + `cps-refresh`. Enables semantic search, knowledge graph, incremental reindex. Requires Python 3.10+.

Installer: `cps-setup` (menu-driven, auto-detects existing Core scaffolds for graceful upgrade). See `Reference/CPS_Design.md` for the full design spec.

---

## 3. Runtime Files

Canonical Python files live in `Runtime/`. See `Runtime/README.md` for the file-by-file manifest and the `pip install` line.

**Self-hosting sync (rev 8).** Every `cps_ingest` call runs `IngestPipeline.sync_runtime_to_cps()` first. It SHA-256-compares each `Runtime/*.py` against the matching `.cps/*.py` and promotes any drifted file via `Path.write_bytes()`. The check is gated on `Runtime/` existing next to `.cps/`, so downstream projects installed via `cps-setup` are unaffected — they have no `Runtime/` directory and the sync silently no-ops. Promoted filenames surface in the ingest response under `runtime_sync.files_promoted`.

---

## 4. Skills

| Skill | File | Trigger phrases | Status |
|-------|------|-----------------|--------|
| `cps-setup` | `Skills/cps-setup.skill` | "install cps", "set up cps", "deploy cps", "bootstrap cps", "install cps core", "install cps full", "upgrade cps to full" | **Canonical** (menu-driven Core or Full installer) |
| `cps-init` | `Skills/cps-init.skill` | "cps-init", "scaffold cps", "initialize cps project" | Active (rev 3 — fetches `cps_scaffold.py` from GitHub main at runtime; no bundled scripts) |
| `cps-query` | `Skills/cps-query.skill` | "cps query [question]", "search knowledge base" | Active |
| `cps-refresh` | `Skills/cps-refresh.skill` | "refresh cps", "reindex" | Active |
| `cps-capture` | `Skills/cps-capture.skill` | "save this pattern", "lesson learned", "worth remembering", "capture this", "cps-capture" | Active |
| `task` | `Skills/task.skill` | "add a task", "mark that done", "task backlog", "show me open tasks" | Active |

---

## 5. Single-Tenant Architecture (rev 11)

CPS is strictly one-project-per-db. Each project has its own `.cps/` directory containing its own `cps.db` and `cps_manifest.json`. There is no shared server, no cross-project search, no ProjectRegistry.

`~/.cps/` is used only as a shared model cache (`~/.cps/models/all-MiniLM-L6-v2/`) so multiple projects on the same machine reuse the same ~90MB ONNX download. It does not contain a registry or any per-project state.

`namespace` remains in `cps_config.json` as a display label only. It does not prefix chunk IDs and does not affect search scoping.

---

## 6. Phase History

**Current:** Phase 8.7 complete. Full changelog: `Reference/CPS_Phase_History.md`. Consult only when historical context is needed; day-to-day work does not require reading it.

**Tested numbers (D3 project):** 132 files, 1097 chunks, 220K tokens indexed. Typical 5-result query: ~1K tokens vs 3K–12K for raw file reads.

---

## 7. Documentation

| File | Location | Lines | TOC | Purpose |
|------|----------|-------|-----|---------|
| CPS_Features_Overview.md | `Documentation/md/` | ~60 | — | All 13 CPS features ranked by impact, with tier groupings and pending items |
| CPS_Setup_Guide.md | `Documentation/md/` | 55 | — | Install flow, profile choice (Core vs Full), configuration walkthrough |
| CPS_Troubleshooting_Guide.md | `Documentation/md/` | 63 | — | Error diagnosis and recovery steps |
| CPS_Design.md | `Reference/` | 206 | — | Canonical design spec — profiles, installer flow, Core/Full delineation |
| CPS_Integration_Spec.md | `Reference/` | 302 | ✅ | **Historical** (Phase 5-era) — EM persona proving ground, tier model, token savings model |
| CPS_Phase_History.md | `Reference/` | — | — | Full changelog from Phase 1 through current |
| CPS_Deployment_Checklist.md | `Reference/` | 17 | — | New-project deployment checklist |
| CPS_Validation_Report.md | `Reference/` | 60 | — | Phase validation results and test outcomes |
| Runtime/README.md | `Runtime/` | 45 | — | File manifest, dependencies, quick install |

**TOC count: 1 doc.** Any doc above 200 lines must have a companion `_TOC.md` per §11. The TOC column is the authoritative registry — if a doc is over threshold and the TOC column is empty, it is out of compliance. (`CPS_Design.md` at 206 lines is marginally over threshold — add a TOC on next edit pass.)

**Canonical source:** CPS indexes and reads from `.md` only. Never read from or index `.html` versions — markdown is the single source of truth and saves 40–60% on token cost.

**Read hierarchy:** This CLAUDE.md first → `Runtime/README.md` for file questions → `_TOC.md` companion → targeted section read with `offset`/`limit`. Full doc reads are last resort.

---

## 8. CPS Usage — On-Demand CLI

CPS runs on demand via skills — no MCP server, no session startup probe required.

- **Query:** invoke `cps-query` skill (or `python .cps/cps_server.py search --query "..."`)
- **Refresh:** invoke `cps-refresh` after doc/code changes
- **Capture:** invoke `cps-capture` for knowledge entries

No `.mcp.json` check needed. Available whenever `.cps/cps_server.py` exists in the project root.

---

## 10. Deployment Checklist (New Project)

Deploying CPS to a new Cowork project? See `Reference/CPS_Deployment_Checklist.md` for the full checklist. `cps-setup` is the canonical install path.
