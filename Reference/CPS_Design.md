# CPS — Design

> **Status:** rev 7 — 2026-04-11: §1 Motivation reframed — CPS is the project management and task-flow system for developing solutions with Claude Cowork; runtime/semantic search kept as Full-profile retrieval layer, not the product identity.
> **Rev 6 — 2026-04-10:** §4.2 Directories and Files updated to include Ideas/, Roadmap/, Input/, Output/ (all scaffolded since Phase 8.7 / cps-patcher p001–p003).
> **Rev 5 — 2026-04-09:** cps-init redesign: profile arg + expanded CLAUDE.md pointer sections + CREATED/REPAIRED/SKIPPED outcome classification formally sanctioned; §4.1–§4.4 updated.
> **Rev 4 — 2026-04-09:** cps-init now scaffolds `Documentation/` and `Documentation/md/` so the default cps-setup Step 10 source path is never empty on a fresh Full install; §4.2 and §4.5 updated together.
> **Rev 3 — 2026-04-08:** t1-cps-design-update: drop any remaining lite/runtime-gating framing, make Core→Full graceful upgrade explicit, clarify prereqs check runs on every Full install, refresh task ID references in §7.
> **Owner:** Shane Huesdon
> **Scope:** Design the CPS Core and CPS Full profiles and the menu-driven `cps-setup` installer that deploys either one. Zero artifact overlap between profiles. Full auto-detects existing Core scaffold and treats it as a graceful upgrade — no lite-mode markers, no runtime gating flags, no divergent wording.

---

## 1. Motivation

CPS is the project management and task-flow system for developing solutions with Claude Cowork. It turns a Cowork project into a place where work gets planned, executed, and learned from across sessions instead of restarting every conversation: tiered task backlog that surfaces the right work on session start, five-bucket knowledge capture that makes decisions and patterns stick, 200-line TOC rule that keeps documentation navigable, and session/delegation discipline that keeps token cost and routing predictable. Retrieval is the supporting layer, not the product — grep on small projects, a local semantic index on large ones.

CPS serves two project sizes. Below ~100 files / ~10K markdown lines, semantic search is solving a problem grep already solves — but the three CPS pillars (task backlog, knowledge capture, TOC rule) still deliver value from day one. Above that threshold, the Python runtime and semantic search earn their keep.

**CPS Core** is the three-pillar profile without the runtime. **CPS Full** is Core plus the runtime and the two query skills. One system, two versions, one installer.

---

## 2. The Two Profiles

### 2.1 CPS Core

**Skill set (three skills):**

- `cps-init` — new skill. Scaffold + CLAUDE.md pointer sections. Idempotent.
- `task` — unchanged. Manages `Reference/Claude/tasks.json`.
- `cps-capture` — unchanged. Writes to `Reference/{Patterns,Decisions,Lessons}/`.

**Excluded:** `.cps/`, Python runtime, `.mcp.json`, `cps-query`, `cps-refresh`, semantic search, graph.

**Retrieval:** grep over `Reference/` and `Documentation/md/`, guided by the 200-line TOC rule.

### 2.2 CPS Full

**Skill set (five skills + runtime):**

- `cps-init` + `task` + `cps-capture` (same as Core)
- `cps-query` — unchanged. Semantic search.
- `cps-refresh` — unchanged. Incremental reindex.
- **Python runtime** — `.cps/`, `cps_server.py`, `cps.db`, `cps_manifest.json`, `cps_config.json`, `.mcp.json`, `~/.cps/models/` cache.

Full is a strict superset of Core. Graduation is additive.

---

## 3. The `cps-setup` Installer

New skill: `cps-setup`. Deprecates the existing `cps-installer.skill`. Menu-driven, dependency-aware, guided install.

### 3.1 Flow

```
[1] Welcome + profile menu (Core | Full)
[2] Prerequisites check
    Core: none
    Full: Python 3.10+, write access — runs on every Full install (fresh and upgrade)
    Full (upgrade): also validate Core scaffold is in place — see §3.2
[3] Install plan shown + single approval gate
[4] Install cps-init → present .skill → user saves → invoke it
    Auto-creates the full Reference/ scaffold and CLAUDE.md
    pointer sections in one pass.
[5] Present task.skill + cps-capture.skill for save/install
[6] (Full only) Present cps-query.skill + cps-refresh.skill
[7] (Full only) Deploy runtime
    Write .cps/, .mcp.json, run cps_ingest, run cps_graph_build
[8] Summary + next steps
```

### 3.2 Core validation on Full upgrade

When the user picks Full on a project that already has (or should have) Core, the installer validates Core before proceeding to runtime deployment. Validation checks:

- `Reference/Claude/` exists
- `Reference/Patterns/_INDEX.md`, `Reference/Decisions/_INDEX.md`, `Reference/Lessons/_INDEX.md` all exist
- `Reference/CPS_Task_Module.md`, `Reference/CPS_TOC_Rule.md`, `Reference/CPS_Capture_Taxonomy.md` all exist
- CLAUDE.md §9, §11, §12 pointer sections present

Any missing piece → installer halts, reports what's missing, offers to run `cps-init` to fix. User must approve the fix before Full install continues. Fresh Full installs (no Core present) run Step 4 normally and skip validation.

### 3.3 Dependency awareness

The installer enforces install order:

- `cps-init` before `task` / `cps-capture` (both need the scaffold)
- Runtime before `cps-query` / `cps-refresh` (both need `.cps/`)
- `.mcp.json` before session restart

User cannot skip ahead. Mid-install bail leaves a consistent intermediate state (a Core install mid-graduation still works as Core).

### 3.4 Deprecation of `cps-installer`

`cps-installer.skill` stays in `Skills/` until `cps-setup` ships and is validated on a fresh project. Then `cps-installer` is archived (moved to `Skills/deprecated/` or similar) with a SKILL.md note pointing to `cps-setup`. No in-place replacement — clean handoff.

---

## 4. The New Skill: `cps-init`

Only new skill this design introduces. Everything else is reuse.

### 4.1 Purpose

One-shot auto-scaffold. Accepts a `profile ∈ {core, full}` argument (default `core`). Creates the full Reference/ file structure and CLAUDE.md pointer sections in a single pass. Re-running is safe (existing files are preserved, not overwritten) but the expected path is "run once at install."

### 4.2 Writes

**Directories:**
- `Reference/Claude/`
- `Reference/Patterns/`
- `Reference/Decisions/`
- `Reference/Lessons/`
- `Documentation/` *(rev 4)*
- `Documentation/md/` *(rev 4 — empty placeholder so the default Full source path resolves)*
- `Reference/Ideas/` *(rev 6 — low-friction idea capture; promote to Roadmap when ready)*
- `Reference/Roadmap/` *(rev 6 — committed intentions with Now/Next/Later horizon)*
- `Input/` *(rev 6 — drop zone for source materials; indexed by Full via `Input/**/*.md`)*
- `Output/` *(rev 6 — default drop zone for Claude-generated deliverables)*

**Files:**
- `Reference/Patterns/_INDEX.md` (per-bucket stub, titled)
- `Reference/Decisions/_INDEX.md` (per-bucket stub, titled)
- `Reference/Lessons/_INDEX.md` (per-bucket stub, titled)
- `Reference/Ideas/_INDEX.md` *(rev 6 — per-bucket stub)*
- `Reference/Roadmap/_INDEX.md` *(rev 6 — per-bucket stub)*
- `Reference/CPS_Task_Module.md` (canonical §9 content)
- `Reference/CPS_TOC_Rule.md` (canonical §11 content)
- `Reference/CPS_Capture_Taxonomy.md` (canonical §12 content)

**`_INDEX.md` stub outcome classification.** For each stub, check in order:
- **SKIPPED** — file exists and is non-empty → preserve user content, do not touch.
- **REPAIRED** — parent dir existed but `_INDEX.md` is missing or empty → write stub (indicates partial previous install).
- **CREATED** — dir was just created and file is absent → write stub normally.

Only write for REPAIRED and CREATED. All three outcomes are reported in the final output.

**CLAUDE.md edits — two-file pointer strategy:**

Writes pointer sections from two embedded template files. Template files hold canonical content; CLAUDE.md stays lean. Rev markers (`<!-- cps-core rev: N -->`, `<!-- cps-full rev: N -->`) gate updates — sections are rewritten only if the embedded rev is newer than the on-disk rev.

**Core sections** (`claudemd_pointers_core.md`, rev marker `<!-- cps-core rev: N -->`):
- `## Delegation` — Haiku Gateway routing summary
- `## Session Startup` — what to do at session open
- `## Document Access Hierarchy` — CLAUDE.md → TOC companions → targeted reads → full reads
- `## Documentation` — where docs live (Reference/ and Documentation/md/)
- `## 9. Task Module — Trigger Summary` — backlog rules pointer
- `## 11. TOC Maintenance Rule` — 200-line TOC rule pointer
- `## 12. Knowledge Capture — Taxonomy` — capture buckets pointer + pre-design read trigger

**Full additions** (`claudemd_pointers_full_additions.md`, rev marker `<!-- cps-full rev: N -->`):
- `## CPS Server Protocol` — on-demand CLI, no MCP daemon, no session startup probe

Always write Core sections. Write Full additions only if `profile == full`.

### 4.3 Does not

- Create `Reference/Claude/tasks.json` — `task` skill owns that on first invoke.
- Touch `.cps/` or `.mcp.json` — `cps-setup` Step 7 owns runtime deployment (Full only).
- Install other skills — `cps-setup` presents them.

### 4.4 Safety contract

- Fresh install: creates the full scaffold in one pass.
- Existing dirs: left alone.
- Existing `_INDEX.md` files: never overwritten when non-empty (see REPAIRED/SKIPPED/CREATED classification in §4.2).
- Existing `Reference/CPS_*.md` canonical docs: updated only if skill-embedded rev is newer.
- CLAUDE.md Core sections: rewritten as a unit only if embedded `cps-core rev` > on-disk `cps-core rev`. Legacy `<!-- rev: N -->` markers treated as cps-core rev 0.
- CLAUDE.md Full additions: rewritten only if embedded `cps-full rev` > on-disk `cps-full rev`.
- User content between, before, or after the pointer sections is never touched.

### 4.5 §11 wording (kept from Full)

The TOC rule in `Reference/CPS_TOC_Rule.md` (and the CLAUDE.md §11 pointer) references both `Reference/` and `Documentation/md/` — same as CPS Full today. As of rev 4, `cps-init` scaffolds `Documentation/md/` empty on every install (Core and Full) so the path always resolves and the §11 rule fires uniformly. The directory may sit empty on Core projects that don't add markdown to it — that's fine and intentional. Forward compat preserved; no divergent wording.

**Why scaffold an empty dir?** Because `cps-setup` Step 10's source-path picker defaults `Documentation/md/**/*.md` ON for Full installs. Pre-rev-4, that default scanned a non-existent directory and produced a 0-file ingest, making fresh Full installs look broken. Pre-creating the empty dir means the default resolves cleanly even on a project that hasn't added any markdown yet.

---

## 5. Graduation: Core → Full

Additive. No migration:

1. User runs `cps-setup` again, picks Full.
2. Installer runs Core validation (§3.2). Halts if anything missing.
3. On pass, re-presents any query/refresh skills not yet installed.
4. Proceeds to Step 7 (runtime).
5. First `cps_ingest` indexes everything the Core project already wrote.

No data move, no schema change, no rewrites. Task backlog, capture buckets, CLAUDE.md pointer sections all carry over untouched.

**Future enhancement:** `cps-setup` detects existing Core install and offers "Upgrade to Full" as a menu shortcut, skipping Step 4–5 re-presentation. Not required for v1.

---

## 6. Deliverables

This task produces:

1. **This document** — `Reference/CPS_Design.md`.
2. **`cps-init.skill` stub** — SKILL.md with full prompt and idempotency contract, minimal scaffold script, pointer-section CLAUDE.md writes. Presented via `mcp__cowork__present_files`. Not production-hardened — iterate after first real use.

Not produced by this task:

- `cps-setup.skill` — follow-up task `t1-cps-setup-build`.
- Modifications to existing `cps-installer`, `task`, `cps-capture`, `cps-query`, `cps-refresh`.

---

## 7. Next steps

1. Shane reviews this rev.
2. Approval → proceed with `t1-cps-setup-build` to build `cps-setup.skill` against this design.
3. On successful Full install validation, run `t2-cps-installer-deprecate` to archive `cps-installer.skill`.
4. Mark `t1-cps-design-update` COMPLETE.
