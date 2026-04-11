# CLAUDE.md

> **Last Updated:** 2026-04-11 (rev 22 — patcher retirement: §0b routing table collapsed to cps-init upgrade path, §1.1 rewritten to solo-developer/multi-project)
> **Status:** Solo-developer dev home. CPS Phase 8.8. Rev history: `Reference/CPS_Phase_History.md`.

<!-- cps-core BEGIN rev: 4 -->
<!-- Managed by cps-init (cps_scaffold.py) — re-run cps-init to update. -->

## Delegation

Route Tier 1–4 mechanical work (file writes, mutations, formatting, transforms) to Haiku. Reserve Sonnet for architecture and decisions. Full heuristic: user preferences.

---

## Session Startup

Surface top 1–3 active tasks via §9 RECOMMEND. Load memory. Proceed to work.

---

## Document Access

Read in order until answered:

1. This CLAUDE.md
2. `_TOC.md` companion (for any `Reference/` or `Documentation/md/` doc over 200 lines)
3. Targeted `offset` / `limit` section read
4. Full doc

### Content Routing

Read the mapped file. Flag missing files via `AskUserQuestion` before creating.

| Topic | File |
|---|---|
| CPS design / profiles / installer flow | `Reference/CPS_Design.md` |
| Runtime Python file manifest | `Runtime/README.md` |
| Phase changelog | `Reference/CPS_Phase_History.md` |
| Task module spec | `Reference/Claude/CPS_Task_Module.md` |
| Capture taxonomy spec | `Reference/Claude/CPS_Capture_Taxonomy.md` |
| TOC rule spec | `Reference/Claude/CPS_TOC_Rule.md` |
| Deployment checklist | `Reference/CPS_Deployment_Checklist.md` |
| Skills inventory | `Reference/Skill_Inventory.md` |

---

## Documentation

- `Reference/` — canonical design docs, patterns, decisions, lessons
- `Documentation/md/` — user-facing markdown docs

---

## Input / Output Folders

- `Input/` — Drop source materials here. CPS (Full profile) indexes `Input/**/*.md` via `source_paths`.
- `Output/` — Default drop zone for Claude-generated deliverables (reports, exports, presentations, one-off artifacts) outside `Documentation/` and `Reference/`. Write deliverables here unless directed elsewhere.

---

## 9. Task Module

Invoke the `task` skill. Session-start RECOMMEND surfaces the tiered backlog from `Reference/Claude/tasks.json`. Spec: `Reference/Claude/CPS_Task_Module.md`.

---

## 11. TOC Rule

Generate a `_TOC.md` companion for every `Reference/` or `Documentation/md/` file over 200 lines. Spec: `Reference/Claude/CPS_TOC_Rule.md`.

---

## 12. Capture Taxonomy

Route captures into five buckets under `Reference/`: Patterns, Decisions, Lessons, Ideas (low-friction — promote when ready), Roadmap (committed intentions, Now/Next/Later horizon). Promote: Idea → Roadmap → Tasks. Trigger phrases: "add idea", "add to roadmap", "promote [title] to roadmap", "promote [title] to tasks". Self-trigger gate: meet all four capture criteria (Ideas accept "what if" thoughts). Spec: `Reference/Claude/CPS_Capture_Taxonomy.md`.

<!-- cps-core END -->

---

## 13. Response Mode

Default chat response: **caveman full**. Scope: response tokens only — files written to `Reference/`, `Documentation/`, `Runtime/`, `Output/`, code blocks, commits, PR bodies, and `SKILL.md` stay prose.

Carveouts to **caveman lite** (preserve nuance):

- Plan mode drafts and `ExitPlanMode` summaries
- Architecture trade-offs and ADR discussions
- Multi-step sequences where fragment order risks misread

Hard prose (no caveman):

- Security warnings and destructive-op gates
- `AskUserQuestion` content (already terse by design)

Escape triggers: `normal mode` reverts to prose; `/caveman lite|full|ultra` adjusts intensity. Level persists to session end.

---

## 0. House Rules

Inherited from global CLAUDE.md — apply to every action in this project.

### 0a. Hard Stops

- `/mnt/.claude/skills/` is read-only. Update path: edit source → rebundle `.skill` in temp → reinstall via `mcp__cowork__present_files`.
- See global `Permanent Instructions` for the approval gate, `AskUserQuestion` rule, and file-truncation recovery.

### 0b. Routing Table

| Trigger | Action |
|---|---|
| Any file read | Read smallest targeted file first → CPS query → `_TOC.md` companion → full doc |
| Any GitHub repo I/O | Use `mcp__github__*` connector against `Huesdon/cowork-project-system` (no subprocess git, no `.bat`). Server registered in project-local `.mcp.json` per `Reference/Decisions/2026-04-11-plugin-decoupling.md`. |
| Edited `Runtime/*.py` | Rebundle `cps-setup.skill` before session close |
| Edited `Reference/cps_scaffold.py` | Push to `main` via `mcp__github__create_or_update_file` before close (fetched at runtime by `cps-init` rev 3+) |
| Added structurally new scaffold artifact (dir, stub, CLAUDE.md section block, Full-profile config key) | Edit `cps_scaffold.py`, bump the relevant `<!-- rev: N -->` marker (canonical doc) or `<!-- cps-core BEGIN rev: N -->` marker (CLAUDE.md block), push to `main`. Re-run `cps-init` against downstream projects to propagate. No patch catalog. |

---

## 1. Project Identity

- **System:** Claude Project System (CPS) — a Claude Cowork project management and task-flow system for developing solutions with Cowork. Four modules (Tasks, Knowledge, Docs, Sessions) keep planning, execution, and institutional memory coherent across every Cowork session.
- **Developer:** Shane Huesdon @ Glidefast Consulting
- **Stack:** Python (on-demand subprocess, MCP/stdio transport), SQLite (sqlite-vec), ONNX (all-MiniLM-L6-v2), Claude Cowork skills
- **Runtime source of truth:** `Runtime/` — canonical Python files
- **Skills install path:** `/mnt/.claude/skills/` (global; every CPS skill runs from here). Stage `.skill` bundles in workspace `Skills/` before hand-install.

### 1.1 Solo-Developer Principle

CPS is a solo-developer, one-machine, multi-project system. One developer (Shane), one machine, one global skill install at `/mnt/.claude/skills/`, any number of Cowork project folders scaffolded via `cps-init` / `cps-setup`. Reject any premise that assumes multi-user sharing, fleet distribution, or cross-machine sync. Decision record: `Reference/Decisions/2026-04-11-cps-permanently-single-tenant.md` (scope-corrected). Upgrade model: `Reference/Decisions/2026-04-11-cps-upgrade-model-two-entry-points.md`.

---

## 2. What CPS Is

Project management and task-flow system for Claude Cowork. Four modules: Tasks (§9), Knowledge (§12), Docs (§11), Sessions (§0/Delegation). Ships as Core (three pillars + grep) or Full (Core + Python runtime + semantic search + knowledge graph). Installer: `cps-setup`. Full spec + module detail + MCP tool list: `Reference/CPS_Design.md`.

---

## 3. Runtime Files

Canonical Python lives in `Runtime/`. See `Runtime/README.md` for the manifest and install. Self-hosting sync (rev 8+): every `cps_ingest` promotes drifted `Runtime/*.py` → `.cps/*.py` via SHA-256 compare; no-ops when `Runtime/` is absent (downstream projects). Promoted filenames surface in `runtime_sync.files_promoted`.

---

## 4. Skills

CPS skill inventory (triggers, bundle paths, status) lives in `Reference/Skill_Inventory.md`. Update that file when adding, retiring, or revving a skill.

---

## 6. Phase History

Phase 8.8 complete (patcher retirement). Changelog + tested numbers: `Reference/CPS_Phase_History.md`.

---

## 7. Documentation

Doc registry (file, location, lines, TOC, purpose) lives in `Documentation/md/_doc_registry.md`. Read and index `.md` only — markdown is the single source of truth (40–60% token savings vs `.html`). Any doc over 200 lines gets a `_TOC.md` companion per §11.

---

## 8. CPS Usage — On-Demand CLI

Run CPS on demand via skills. Available whenever `.cps/cps_server.py` exists in the project root.

| Action | Invocation |
|---|---|
| Query | `cps-query` skill (or `python .cps/cps_server.py search --query "..."`) |
| Refresh index | `cps-refresh` skill after doc/code changes |
| Capture knowledge | `cps-capture` skill |

---

## 10. Deployment Checklist (New Project)

Deploying CPS to a new Cowork project? See `Reference/CPS_Deployment_Checklist.md` for the full checklist. `cps-setup` is the canonical install path.
