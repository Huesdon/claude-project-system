# CPS Features — Ranked by Impact

> As of Phase 8.7 · 2026-04-11

**CPS is a Claude Cowork project management and task-flow system for developing solutions with Cowork.** Four modules — Tasks, Knowledge, Docs, Sessions — keep planning, execution, and institutional memory coherent across every Cowork session. The features below are ranked by how much lift each one provides on top of that core loop.

---

## Tier 1 — Foundational (session-to-session survival)

**1. Semantic Knowledge Index** *(Full profile)*
Local SQLite + ONNX index over all project markdown. Answers queries in ~1K tokens vs 3K–12K for raw file reads. The single biggest token-cost reducer in the system. Everything else builds on this.

**2. Task Backlog (`task` skill)**
Cross-session single source of truth in `tasks.json`. Without it, context resets every conversation and nothing accumulates. The reason you can pick up where you left off.

**3. Knowledge Capture Taxonomy** *(Patterns / Decisions / Lessons / Ideas / Roadmap)*
Five-bucket system for institutional memory. Decisions stop getting relitigated. Patterns stop getting reinvented. The compounding value increases the longer a project runs.

**4. Document Access Hierarchy**
CLAUDE.md → `_TOC.md` → targeted read → full read. Enforces reading the smallest possible file first. Without this discipline, token cost balloons fast on any project with significant docs.

---

## Tier 2 — Operational (day-to-day quality)

**5. Haiku Delegation Model**
Routing mechanical work (file writes, mutations, formatting) to Haiku while Sonnet handles decisions. Meaningful cost reduction on any session with repeated tool calls.

**6. `cps-setup` Installer** *(menu-driven Core/Full)*
Turnkey deployment with profile detection and graceful Core→Full upgrade. Removes the friction that would otherwise prevent CPS from spreading to new projects.

**7. Incremental Reindex (`cps-refresh`)**
Hash-based change detection — only re-chunks and re-embeds what changed. Makes keeping the index current fast enough to actually do it.

**8. TOC Maintenance Rule**
Companion `_TOC.md` for any doc over 200 lines. Keeps large docs navigable without full reads. Low-glamour but essential at scale.

**9. Plugin Discovery as Solution Step**
Before concluding a capability doesn't exist, search the MCP registry and suggest connectors. Plugins are a first-class option in any workflow touching external tools, data sources, or services. Enforced in global CLAUDE.md.

**10. Input/Output Folder Conventions**
`Input/` for source materials Claude picks up and analyzes; `Output/` as the default drop zone for deliverables. Removes ambiguity about where things land and keeps the workspace predictable.

**11. Ideas→Roadmap→Tasks Promotion Loop**
When the task backlog empties, surface roadmap items; when roadmap is empty, surface ideas. Closes the loop between long-horizon thinking and active work. Managed by the `task` skill.

---

## Tier 3 — Integrity & Lifecycle

**12. `cps-patcher` Skill**
Incremental upgrades to existing CPS projects without reinstall. Idempotent, catalog-ordered, manifest-tracked. Keeps downstream projects current without regression risk.

**13. Self-Hosting Sync** *(Runtime/ → .cps/ on ingest)*
SHA-256 comparison on every `cps_ingest` call promotes any drifted `Runtime/*.py` into `.cps/`. Prevents the CPS dev project from running stale code against itself.

**14. Knowledge Graph** *(`cps_graph_build` / `cps_graph_query`)*
Relationship traversal across the index. Higher ceiling than flat search but requires a populated index to show value. Impact grows with project maturity.

**15. `cps-init` Rev 3 — Runtime GitHub Fetch**
Fetches `cps_scaffold.py` from `raw.githubusercontent.com/Huesdon/claude-project-system/main` at runtime. Scaffold edits go live to all downstream projects the moment they're pushed — no skill rebundle required.

**16. GitHub MCP as Canonical CPS Dev I/O**
All reads, writes, and pushes during CPS dev sessions go through `mcp__github__*` directly. No subprocess git, no `.bat` helpers, no manual push step. Mount-corruption risk eliminated.

**17. Patch Catalog Discipline**
Any structurally new scaffolded artifact requires a same-session `patch-index.md` entry + per-patch file, pushed atomically to `main`. Shrinks the gap between "shipped" and "downstream can get it" to zero.
