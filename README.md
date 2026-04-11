# Claude Project System (CPS)

> A Claude Cowork project management and task-flow system for developing solutions with Cowork.

CPS turns a Claude Cowork project into a place where work gets planned, executed, and learned from across sessions — instead of restarting every conversation. It installs four modules into any Cowork project and wires them into the project `CLAUDE.md` so every session picks up where the last one left off.

## The Four Modules

1. **Tasks** — Tiered backlog (`tasks.json`, T1/T2/T3/Roadmap) surfaced at session start. Managed by the `task` skill. The daily flow: add, prioritize, work, log, promote.
2. **Knowledge** — Five-bucket capture (Patterns / Decisions / Lessons / Ideas / Roadmap) under `Reference/`. Written via `cps-capture`. Decisions stop getting relitigated; ideas become roadmap items become shipped tasks.
3. **Documentation** — Markdown-first single source of truth. 200-line TOC companion rule keeps large docs navigable without full reads.
4. **Sessions** — Document access hierarchy, routing rules, and Haiku delegation that make every Cowork session cheap, predictable, and continuous with the last one.

## Two Profiles

- **Core** — Scaffold + three pillars (tasks, capture, TOC). Retrieval is grep over `Reference/` and `Documentation/md/`. No Python runtime required. Right fit for projects under ~100 files.
- **Full** — Core plus a local Python runtime and a SQLite + sqlite-vec + ONNX semantic index over project markdown. Answers cited queries in ~1K tokens vs 3K–12K for raw reads. Adds `cps-query`, `cps-refresh`, and the knowledge graph. Requires Python 3.10+.

Full is a strict superset of Core — graduation is additive, no migration. One system, two versions, one installer.

## Install

In any Cowork session, say **"install cps"** or **"set up cps"** to invoke the `cps-setup` skill. It will ask Core vs Full, auto-detect any existing scaffold, run prerequisites, and present the skill bundles for save/install.

Full setup guide: [`Documentation/md/CPS_Setup_Guide.md`](Documentation/md/CPS_Setup_Guide.md)
Design spec: [`Reference/CPS_Design.md`](Reference/CPS_Design.md)

---

## Features — Ranked by Impact

> As of Phase 8.7 · 2026-04-11

### Tier 1 — Foundational (session-to-session survival)

**1. Task Backlog (`task` skill)**
Cross-session single source of truth in `tasks.json`. Without it, context resets every conversation and nothing accumulates. The reason you can pick up where you left off.

**2. Knowledge Capture Taxonomy** *(Patterns / Decisions / Lessons / Ideas / Roadmap)*
Five-bucket system for institutional memory. Decisions stop getting relitigated. Patterns stop getting reinvented. Compounding value grows the longer a project runs.

**3. Semantic Knowledge Index** *(Full profile)*
Local SQLite + ONNX index over all project markdown. Answers queries in ~1K tokens vs 3K–12K for raw file reads. The single biggest token-cost reducer once a project is large enough to need it.

**4. Document Access Hierarchy**
CLAUDE.md → `_TOC.md` → targeted read → full read. Enforces reading the smallest possible file first. Without this discipline, token cost balloons fast on any project with significant docs.

### Tier 2 — Operational (day-to-day quality)

**5. Haiku Delegation Model**
Routing mechanical work (file writes, mutations, formatting) to Haiku while Sonnet handles decisions. Meaningful cost reduction on any session with repeated tool calls.

**6. `cps-setup` Installer** *(menu-driven Core/Full)*
Turnkey deployment with profile detection and graceful Core→Full upgrade. Removes the friction that would otherwise prevent CPS from spreading to new projects.

**7. Incremental Reindex (`cps-refresh`)**
Hash-based change detection — only re-chunks and re-embeds what changed. Makes keeping the index current fast enough to actually do it.

**8. TOC Maintenance Rule**
Companion `_TOC.md` for any doc over 200 lines. Keeps large docs navigable without full reads. Low-glamour but essential at scale.

### Tier 3 — Integrity & Lifecycle

**9. `cps-patcher` Skill**
Incremental upgrades to existing CPS projects without reinstall. Idempotent, catalog-ordered, manifest-tracked. Keeps downstream projects current without regression risk.

**10. Self-Hosting Sync** *(Runtime/ → .cps/ on ingest)*
SHA-256 comparison on every `cps_ingest` call promotes any drifted `Runtime/*.py` into `.cps/`. Prevents the CPS dev project from running stale code against itself.

**11. Knowledge Graph** *(`cps_graph_build` / `cps_graph_query`)*
Relationship traversal across the index. Higher ceiling than flat search but requires a populated index to show value. Impact grows with project maturity.

---

## Status

Phase 8.7 · Single-tenant dev home (one developer, one machine, one forever-home project).
