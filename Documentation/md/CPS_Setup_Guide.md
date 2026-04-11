# Claude Project System (CPS) Setup Guide

## What is CPS?

CPS is **a Claude Cowork project management and task-flow system for developing solutions with Cowork.** It turns a Cowork project into a place where work gets planned, executed, and learned from across sessions — not restarted every conversation. Four modules deliver it, all wired into the project `CLAUDE.md` during install:

1. **Task Management** — Tiered backlog in `Reference/Claude/tasks.json` (T1/T2/T3/Roadmap), surfaced at session start, managed by the `task` skill. The daily flow: add, prioritize, work, log, promote.
2. **Knowledge Management** — Five-bucket capture (Patterns / Decisions / Lessons / Ideas / Roadmap) under `Reference/`, written via `cps-capture`. Decisions stop getting relitigated, ideas become roadmap items become shipped tasks.
3. **Documentation Management** — Markdown-first single-source-of-truth under `Documentation/md/` and `Reference/`, enforced by the 200-line TOC companion rule so large docs stay navigable.
4. **Session & Token Management** — Document access hierarchy, routing table, and Haiku delegation rules that make each Cowork session cheap, predictable, and continuous with the last one.

**Retrieval layer.** Full profile adds a local semantic index (SQLite + sqlite-vec + ONNX `all-MiniLM-L6-v2`) that ingests project markdown and JSON and answers cited queries in ~1K tokens instead of 3–12K for raw reads. Invoked on demand via subprocess CLI — no background process. On smaller projects, grep over `Reference/` and `Documentation/md/` does the same job.

**CPS ships in two profiles:**

- **Core** — Scaffold + three pillars only. Creates the folder structure (`Documentation/`, `Reference/`, `Input/`, `Output/`), the three knowledge buckets (`Reference/Patterns/`, `Decisions/`, `Lessons/`) with `_INDEX.md` files, and writes the task/TOC/capture rules into `CLAUDE.md`. Skills: `cps-init`, `task`, `cps-capture`. No Python runtime required. Retrieval is grep over `Reference/` + `Documentation/md/`, guided by the TOC rule. Use this when you want the four-module operating discipline without semantic search.
- **Full** — Core plus the Python runtime (`Runtime/`) and a local SQLite vector database (`.cps/`). Adds `cps-query` (semantic search with citations), `cps-refresh` (incremental re-index), and the knowledge graph. Requires Python 3.10+ and pip. Full is a strict superset of Core — graduation is additive, no migration.

## Installing CPS

In any Cowork session, say **"install cps"** or **"set up cps"** to invoke the `cps-setup` skill. It will:

1. Ask whether you want **Core** or **Full**.
2. Auto-detect any existing Core scaffold and perform a graceful additive upgrade if you choose Full.
3. Install the runtime and run an initial ingest (Full only).
4. Present `cps-query`, `cps-refresh`, and `cps-capture` skills for save/install.

## What Gets Indexed (Full only)

CPS scans source paths defined in `.cps/cps_config.json`. Defaults:

- `Documentation/md/**/*.md`
- `Reference/**/*.md`
- `Input/**/*.md` (if present)

Markdown files are split by heading structure. JSON files (if included in `source_paths`) are split by array or top-level key. Binary and HTML files are ignored — markdown is the canonical source.

## Available Skills

| Skill | Purpose |
|-------|---------|
| `cps-setup` | Canonical installer — Core or Full, new or upgrade |
| `cps-query` | Semantic search with citations |
| `cps-refresh` | Incremental re-index after doc changes |
| `cps-capture` | Save patterns, decisions, and lessons to the second brain |

## Configuration (Full only)

`.cps/cps_config.json` controls indexing behavior. Key fields:

- `source_paths` — glob patterns for indexed files
- `cache.similarity_threshold` — semantic match strictness (default `0.05`)
- `cache.max_age_hours` — cache TTL (default `24`)

## After Editing Docs

Run `cps-refresh` after any documentation changes. CPS compares file hashes and re-processes only what changed — incremental, not full re-ingest.

## Graduating Core to Full

Run `cps-setup` in a project with an existing Core scaffold. The installer auto-detects the scaffold and offers a Full upgrade — it preserves your existing files and adds only the Python runtime and `.cps/` configuration.
