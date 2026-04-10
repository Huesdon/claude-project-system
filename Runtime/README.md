# CPS Runtime

**Status:** Phase 8.7 complete (2026-04-09)
**Design Spec:** `Reference/CPS_Design.md`
**Setup Guide:** `Documentation/md/CPS_Setup_Guide.md`
**Troubleshooting:** `Documentation/md/CPS_Troubleshooting_Guide.md`
**Phase History:** `Reference/CPS_Phase_History.md`

CPS is a context engine with four modules — Knowledge, Tasks, Docs, Sessions. This directory contains the canonical Python source for the **Full profile** engine (semantic index, embedder, graph). Core profile deployments do not need these files.

## Files

| File | Purpose |
|------|---------|
| `cps_server.py` | MCP server + ingest pipeline. Tools: `cps_search`, `cps_retrieve`, `cps_status`, `cps_ingest`, `cps_prime`, `cps_purge`, `cps_graph_build`, `cps_graph_query`. JSON-RPC 2.0 over stdio. Also exposed via subprocess CLI (`python .cps/cps_server.py search --query "..."`). Includes semantic cache, persona-boosted scoring, and the `sync_runtime_to_cps()` self-hosting hook. |
| `cps_chunker.py` | Markdown + JSON chunker. Splits `.md` by `##`/`###` headings, `.json` by array entries or top-level keys. Merges dust (<50t), splits oversized (>2000t) at paragraph/line boundaries. Universal `chunk_file()` dispatcher routes by extension. |
| `cps_embedder.py` | ONNX embedder. Downloads `all-MiniLM-L6-v2` from HuggingFace on first run into `~/.cps/models/` (shared across all projects on the machine), generates 384-dim L2-normalized vectors via onnxruntime. |
| `cps_graph.py` | Knowledge graph builder. Scans indexed chunks for cross-references (file paths, schemas, skills) and builds a queryable relationship graph in SQLite. Supports BFS traversal, orphan detection, cluster analysis. |
| `cps_config.json` | Default config template. Set `project_root` and `source_paths` before deploying. Includes cache settings. |

## Dependencies

```
pip install sqlite-vec huggingface-hub tokenizers --break-system-packages
# onnxruntime and numpy are pre-installed in the Cowork sandbox
```

## Quick Install

Run **"install cps"** in any Cowork session to invoke the canonical `cps-setup` skill. It will prompt for Core or Full, handle graceful Core→Full upgrades, install the runtime, run initial ingest, and present the sub-skills (`cps-query`, `cps-refresh`, `cps-capture`) for save/install.

## Skills (Full profile)

| Skill | File | Trigger |
|-------|------|---------|
| `cps-setup` | `Skills/cps-setup.skill` | "install cps", "set up cps", "deploy cps" |
| `cps-init` | `Skills/cps-init.skill` | "scaffold cps", "initialize cps project" |
| `cps-query` | `Skills/cps-query.skill` | "cps query [question]", "search knowledge base" |
| `cps-refresh` | `Skills/cps-refresh.skill` | "refresh cps", "reindex" |
| `cps-capture` | `Skills/cps-capture.skill` | "save this pattern", "lesson learned" |
| `task` | `Skills/task.skill` | "add a task", "mark that done", "task backlog" |

Core profile ships a reduced set: `cps-init`, `task`, `cps-capture` (no query/refresh, no runtime).

## Self-Hosting Sync

Every `cps_ingest` call runs `IngestPipeline.sync_runtime_to_cps()` first. It SHA-256-compares each `Runtime/*.py` against the matching `.cps/*.py` and promotes any drifted file via `Path.write_bytes()`. The check is gated on `Runtime/` existing next to `.cps/`, so downstream projects (installed via `cps-setup`, no `Runtime/` directory) silently no-op. Promoted filenames surface in the ingest response under `runtime_sync.files_promoted`.

## Tested Numbers

- 132 files scanned, 1097 chunks, 220K tokens indexed
- Average chunk: ~201 tokens
- Typical 5-result query: ~1K tokens vs 3K–12K for a raw file read
- Incremental re-ingest: 130/132 files skipped (unchanged) on second run
