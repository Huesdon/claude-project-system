# Layered CLAUDE.md Architecture for Token-Efficient Sessions

**Captured:** 2026-04-09
**Applies to:** Claude Cowork projects, CPS-backed projects, any multi-doc project context

## Context
CLAUDE.md files accumulate over time — session rules, tool delegation rules, startup protocols, task management, and token hygiene all compete for the same space. Without structure, CLAUDE.md becomes a monolithic doc that gets read top-to-bottom at every session start, burning tokens on rules that don't apply to the current workstream.

## Technique

Organize CLAUDE.md content into five discrete layers, each with a single responsibility:

**Layer 1 — What to read (and when to stop)**
Answer from loaded CLAUDE.md context first. If not enough: project brief → TOC companion (~200 tokens) → targeted offset/limit section read → full doc only as last resort, with a pause to ask. Never read HTML when markdown exists.

**Layer 2 — How to execute (Haiku delegation)**
Defined once in system instructions only. Sonnet decides; Haiku executes all Tier 1–4 mechanical work (file writes, transforms, bounded searches, guided inserts). File writes >100 lines always delegate. No redundant copy in CLAUDE.md.

**Layer 3 — Session boundaries**
One workstream per session. Soft close signal at ~15 exchanges or topic shift. Hard close signal after any task COMPLETE. On context fill before a natural close point: summarize work done, decisions, and next steps to `session-summary-YYYY-MM-DD.md` in the project folder and surface the path in chat — so the next session can load a single compact file instead of reconstructing context.

**Layer 4 — Task state as context proxy**
`tasks.json` holds only active T1/T2 items. Completed tasks offloaded to `tasks_completed.log`. RECOMMEND is conditional — fires only when the user opens without stated intent. Startup reads the active queue only; `tasks_backlog.json` never loaded at startup.

**Layer 5 — Efficient tooling**
Grep targeted to specific paths. Independent calls batched in parallel. No re-reads of files already in session.

## When to use
- Designing or refactoring a CLAUDE.md for any non-trivial Cowork project
- When CLAUDE.md has grown past ~300 lines and startup feels slow or noisy
- When multiple workstreams share the same project context
- When session token cost is a concern

## When NOT to use
- Single-purpose, single-session projects where a flat CLAUDE.md is clearer
- Projects without CPS or a task backlog (Layers 4–5 have less payoff)

## Examples

**Example 1 — CPS project CLAUDE.md**
The CPS project CLAUDE.md uses exactly this structure: §0 house rules (Layer 1 read hierarchy), §0.1 delegation planning (Layer 2), §8 session startup (Layer 3 boundary signals), §9 task module (Layer 4 conditional RECOMMEND), §7 doc table (Layer 5 targeted reads).

**Example 2 — D3 design project**
The Delivery 3.0 project separates skill inventory, persona tables, and cross-persona write rules into dedicated Reference docs, keeping CLAUDE.md to trigger lists only. Session startup reads only the active task queue — full persona files load on demand.

## Underlying Principle
Minimize tokens loaded at session start. Stop reading as early as possible. Execute mechanics cheaply via Haiku. Never let a session close without leaving a breadcrumb (`session-summary-YYYY-MM-DD.md`) for the next one.
