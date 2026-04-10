# CPS Troubleshooting Guide

Claude Project System — on-demand CLI semantic search for Claude Cowork projects. CPS runs via `python .cps/cps_server.py` on demand (no persistent MCP server). Most issues fall into three categories: install failures, index problems, and search quality.

## Install Issues

### `cps-setup` fails mid-install

Run `pip install sqlite-vec onnxruntime huggingface-hub tokenizers --break-system-packages` manually in a Bash cell, then re-run `cps-setup`. The installer requires network access for the pip install and the initial model download.

### Python not found

Full CPS requires Python 3.10+. Verify with `python --version` in a Bash cell. If missing, install CPS Core instead — it has no Python dependency.

## Dependency Issues

### `sqlite-vec` install fails

Ensure the Cowork sandbox has network access. Run: `pip install sqlite-vec --break-system-packages`. If behind a proxy, contact your administrator.

### Model download fails

The ONNX embedding model (~80MB) downloads from HuggingFace on first run to `~/.cps/models/all-MiniLM-L6-v2/` — shared across all CPS projects on the machine. If network is blocked, manually place `model.onnx` and `tokenizer.json` at that path. Older installs may have cached the model under `Runtime/models/all-MiniLM-L6-v2/` — the embedder auto-migrates this on next run.

### Model re-downloads on every new project

Cause: pre-rev-7 `cps_embedder.py` cached under the project-local `Runtime/models/` instead of `~/.cps/models/`. Fix: upgrade via `cps-setup` — the rev-7+ embedder writes to the shared cache and auto-migrates legacy paths.

## Index Issues

### Empty index (0 chunks)

Verify `source_paths` in `.cps/cps_config.json` match actual file locations. Run `python .cps/cps_server.py ingest` and examine output for glob-matching errors. Confirm files exist at the paths the glob patterns match.

### Stale results after editing docs

Run the `cps-refresh` skill (or `python .cps/cps_server.py ingest`). Verify the edited file's path is covered by a `source_paths` glob pattern in `cps_config.json`.

### JSON files not indexed

Ensure `source_paths` includes JSON glob patterns (e.g., `data/**/*.json`). JSON chunking splits by array or top-level key.

## Search Issues

### Low relevance scores

Scores below 0.25 indicate a weak semantic match. Rephrase the query using terminology from the actual documents. Run `cps-refresh` to confirm the target content is indexed.

### Cache returning stale results

Run `python .cps/cps_server.py purge` to clear the semantic cache. The cache also auto-clears on any ingest or purge operation.

## Graph Issues

### Graph empty or missing edges

Run `python .cps/cps_server.py graph_build` after ingesting. The graph detects cross-references by parsing file paths and schema names in chunk text. Small indexes naturally have few edges — this is expected.

## Performance

### Slow ingest

First ingest downloads the model and processes all files sequentially. Subsequent ingests are incremental (hash-based). Large projects (200+ files) may require 30–60 seconds for a full ingest — this is normal.

### High token usage

CPS returns ~1K tokens per query vs 3–12K for raw file reads. Monitor cache hit rate via `python .cps/cps_server.py status`.
