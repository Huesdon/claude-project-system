# CPS Features — Ranked by Impact

> As of Phase 8.7 · 2026-04-10

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

---

## Tier 3 — Integrity & Lifecycle

**9. `cps-patcher` Skill**
Incremental upgrades to existing CPS projects without reinstall. Idempotent, catalog-ordered, manifest-tracked. Keeps downstream projects current without regression risk.

**10. Self-Hosting Sync** *(Runtime/ → .cps/ on ingest)*
SHA-256 comparison on every `cps_ingest` call promotes any drifted `Runtime/*.py` into `.cps/`. Prevents the CPS dev project from running stale code against itself.

**11. Knowledge Graph** *(`cps_graph_build` / `cps_graph_query`)*
Relationship traversal across the index. Higher ceiling than flat search but requires a populated index to show value. Impact grows with project maturity.

---

## Pending — Not Yet Shipped

**12. Ideas→Roadmap→Tasks Promotion Loop**
When task backlog empties, surface roadmap; if roadmap empty, surface ideas. Closes the loop between long-horizon thinking and active work. Currently a manual step.

**13. Patch Catalog Discipline** *(house rule, no tooling yet)*
Enforcing that new patchable features get catalog entries same-session. The gap between "we shipped it" and "downstream projects can get it" shrinks to zero when this is automatic.
