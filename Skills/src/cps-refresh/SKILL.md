---
name: cps-refresh
description: >
  Shared skill — incrementally re-indexes the project's CPS knowledge base via subprocess CLI
  (no MCP required). Scans configured source paths, detects changed and deleted files via hash
  comparison, re-chunks and re-embeds only what changed, purges stale chunks, rebuilds the
  knowledge graph, and reports results. Supports targeted refresh via explicit file list.
  Triggers on: "refresh cps", "reindex", "update knowledge base", "cps-refresh", "rescan docs",
  "cps reindex", "sync knowledge base", "purge cps".
---

# cps-refresh — Incremental Re-Index, Purge, and Graph Rebuild

## Purpose

Keep the CPS semantic index current without a full rebuild. Detects which files changed since the
last ingest, re-processes only those files, purges stale chunks, rebuilds the knowledge graph,
and reports what changed. No MCP server or `.mcp.json` wiring required — all calls use subprocess.

## Prerequisites

- CPS must be initialized: `.cps/` exists with `cps_server.py`, `cps.db`, and `cps_config.json`
- If `.cps/cps_server.py` not found: "CPS isn't set up. Run the `cps-setup` skill first."

## Finding the Project Root

Use Glob to find `.cps/cps_server.py` in the workspace. The parent of `.cps/` is the project
root. All subprocess commands run from this directory via the Bash tool.

## Execution Flow

### Step 1: Determine Mode

Parse the user's request:

- **Full refresh** (default): "refresh cps", "reindex", "sync knowledge base"
- **Targeted refresh**: "refresh cps for Reference/MyDoc.md" — extract the file path(s)
- **Purge only**: "purge cps", "clean up stale chunks"

### Step 2: Run Ingest

Skip for purge-only mode.

**Full refresh:**
```bash
python .cps/cps_server.py ingest
```

**Targeted refresh:**
```bash
python .cps/cps_server.py ingest --files=path/to/file1.md,path/to/file2.md
```

Parse the JSON result:
- `files_scanned`, `files_processed`, `files_skipped`, `files_deleted`
- `chunks_created`, `chunks_removed`, `total_chunks`, `total_tokens`
- `duration_seconds`, `cache_cleared`

On non-zero exit: report `{"error": "..."}` from stdout and go to Error Handling.

### Step 3: Purge Stale Chunks

```bash
python .cps/cps_server.py purge
```

With age-based purge (optional):
```bash
python .cps/cps_server.py purge --max_age_days=30
```

Parse the JSON result:
- `chunks_removed`, `cache_cleared`

### Step 4: Rebuild Knowledge Graph

Only if Steps 2–3 changed anything (`files_processed > 0` or `chunks_removed > 0`):

```bash
python .cps/cps_server.py graph_build
```

Parse: `nodes`, `edges`. Skip this step if nothing changed.

### Step 5: Report Results

**Changes found:**
```
CPS refresh complete.
- Scanned: [files_scanned] files
- Re-indexed: [files_processed] files ([chunks_created] chunks added, [chunks_removed] removed)
- Deleted: [files_deleted] files removed from index
- Purged: [chunks_removed] stale chunks
- Graph: [nodes] nodes, [edges] edges (rebuilt)
- Total index: [total_chunks] chunks (~[total_tokens] tokens)
- Duration: [duration_seconds]s
```

**Nothing changed:**
```
CPS index is current. [files_scanned] files scanned, all unchanged. [total_chunks] chunks in index.
```

**Purge-only:**
```
CPS purge complete. Removed [chunks_removed] stale chunks. Cache cleared: [cache_cleared].
```

### Step 6: Report Stale Source Paths (Optional)

After ingest, check if any configured `source_paths` in `cps_config.json` matched zero files.
If so, warn:

```
These source paths matched no files — check if they're still valid:
- [path_1]
- [path_2]
```

## Error Handling

- **Non-zero exit / `{"error": "..."}` in stdout:** Report the error. Common causes: database
  locked, disk full, embedding model not downloaded (run `cps-setup` to redeploy the runtime).
- **`purge` error:** Report the error. The index is still usable — purge failure doesn't corrupt
  existing data.
- **`graph_build` error:** Report the error. Search still works without the graph — graph queries
  will return stale results until the next successful build.
- **Source paths match no files:** Warn (Step 6) but don't treat as failure.

## Multi-Engagement Purge

When a consultant switches engagement folders (via cp-setup swap), stale chunks from the
previous engagement's paths fail the disk-existence check. Running cps-refresh after a swap
automatically cleans these up via Step 3's purge. Suggest a refresh after any cp-setup swap.