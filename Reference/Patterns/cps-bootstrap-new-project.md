# Pattern: Bootstrapping and upgrading a CPS project

**Created:** 2026-04-11
**Related decisions:** `Reference/Decisions/2026-04-11-cps-upgrade-model-two-entry-points.md`, `Reference/Decisions/2026-04-11-cps-permanently-single-tenant.md`

## Purpose

Single reference for how to stand up CPS in a new Cowork project folder and how to bring an existing CPS-managed project up to date after a scaffold or runtime change lands on `main`. Covers the decision tree, the profile menu, and what each entry point is (and is not) allowed to touch.

## Pre-requisites

Before bootstrapping any project, verify the five pillar skills are installed globally at `/mnt/.claude/skills/`: `cps-init`, `task`, `cps-capture`, `cps-query`, `cps-refresh`. `cps-setup` Step 1 halts if any are missing. If you see that halt, rebundle the missing pillar from `Skills/src/<name>/` via `python Skills/tools/rebundle.py <name>` and hand-install the resulting `.skill` via `mcp__cowork__present_files`.

## Entry points

CPS has exactly two upgrade entry points, each covering a disjoint surface. This table is the short answer.

| You want to... | Use | Touches |
|---|---|---|
| Scaffold a new Cowork project folder (fresh install) | `cps-setup` | Reference/ tree, CLAUDE.md §9/§11/§12 pointer sections, canonical docs, (optional) `.cps/` runtime |
| Propagate a scaffold change (new bucket, new CLAUDE.md block, bumped canonical doc rev) to an existing project | `cps-init` | Rev-gated edits to the scaffold only. Idempotent. Never touches `.cps/`, `cps.db`, or `cps_config.json`. |
| Propagate a runtime change (edited `Runtime/*.py`) to an existing Full-profile project | `cps-setup` → "Upgrade runtime" | `.cps/*.py` bytes only. Keeps index and config. No ingest. |
| Recover from a corrupted index or a destructive schema change | `cps-setup` → "Reinstall" | Deletes `cps.db`, `cps.db-journal`, `cps_manifest.json`, then full redeploy + full reindex. Never touches source docs. |

If your need fits none of these (e.g. a `tasks.json` schema migration, a `cps.db` schema bump, a non-rev-gated doc edit), build a purpose-specific skill for that case. Do not resurrect a general-purpose patch catalog — that path was retired 2026-04-11.

## Fresh install walkthrough

1. **Drop into the target Cowork folder.** Select the project folder via Cowork's folder picker so it mounts at `/sessions/<id>/mnt/<folder>/`.
2. **Invoke `cps-setup`.** It auto-detects `existing_runtime` and `existing_core`. For a fresh folder both are false, so it presents the profile menu.
3. **Pick a profile:**
   - **Core** — scaffold + pillars only. Grep retrieval. Zero runtime. Best for projects under ~100 markdown files.
   - **Full** — Core + `.cps/` Python runtime + SQLite semantic index + ONNX embeddings + knowledge graph. Best for projects over ~100 files / ~10K markdown lines.
4. **Approve the install plan.** One gate. `cps-setup` writes the scaffold via `cps-init`, (on Full) deploys `.cps/`, collects source paths, writes `cps_config.json`, installs pip deps, runs initial ingest, builds the graph, and runs the test suite. Any step failure halts before the summary.
5. **Done.** The project now has `Reference/`, the CLAUDE.md pointer sections, and (on Full) a working `.cps/cps_server.py` CLI.

## Upgrade walkthrough — scaffold drift

Symptoms: a new bucket landed on `main`, a canonical doc got a rev bump, a CLAUDE.md `<!-- cps-core BEGIN rev: N -->` block got rewritten, or you're not sure whether your scaffold is current.

1. **Invoke `cps-init` against the project.** It fetches `cps_scaffold.py` from GitHub `main` and runs it in-process.
2. **`cps_scaffold.py` is rev-gated and idempotent.** It writes a file only when the skill-embedded rev exceeds the on-disk rev. Unchanged files are skipped. Missing buckets are created. Existing bucket indexes are preserved. CLAUDE.md content outside the fenced `<!-- cps-core BEGIN -->` / `<!-- cps-core END -->` blocks is preserved.
3. **Review the outcome classification.** Each action is reported as `CREATED`, `UPDATED`, `REPAIRED`, or `SKIPPED`. `SKIPPED` means the on-disk rev is already current.

**Warning.** Content *inside* a `cps-core` fenced block in CLAUDE.md is replaced when the skill bumps the block rev. Move hand-edits outside the fenced block, or into a new section, before running `cps-init`. This is by design — fenced blocks are managed territory.

## Upgrade walkthrough — runtime drift

Symptoms: `Runtime/*.py` has been edited upstream and the local `.cps/*.py` is stale, or you want to pick up a bug fix.

1. **Invoke `cps-setup` against the project.** `existing_runtime` is true, so it presents the runtime menu.
2. **Pick "Upgrade runtime."** `cps-setup` redeploys the five `.cps/*.py` modules using `Path.write_text()` (not `shutil.copy`, which truncates on Cowork FUSE mounts), asserts each file's line count matches the source, and runs `py_compile` on each to catch corruption. Keeps `cps.db`, `cps_config.json`, `cps_manifest.json`. Does not reingest.
3. **Re-verifies pip deps.** `pip install --break-system-packages` is a no-op when versions match, but the post-install import check catches any ABI drift.
4. **Runs the test suite.** Any failure halts before the summary — a failed install must not report success.

## Upgrade walkthrough — reinstall (destructive, explicit)

Symptoms: `cps.db` is corrupted, you hit a schema change that requires a ground-up rebuild, or your index is out of sync with the source docs and a `cps-refresh` can't recover it.

1. **Invoke `cps-setup`.** It presents the runtime menu.
2. **Pick "Reinstall."** `cps-setup` deletes `cps.db`, `cps.db-journal`, and `cps_manifest.json`, then runs the full Full-profile install flow: redeploy `.cps/`, collect source paths, rewrite `cps_config.json`, install deps, initial ingest, graph build, test suite.
3. **What is NOT touched.** `Reference/`, `Documentation/`, `Runtime/`, `Input/`, `Output/`, and anything else outside `.cps/` — these are your source docs and CPS never deletes them. Only the index and its manifests are wiped.

## When neither entry point is the right answer

Four signals that you need a new purpose-specific skill instead of re-running `cps-init` or `cps-setup`:

- **A schema bump that requires rewriting every row of an existing file** (e.g. every task in `tasks.json` gets a new field that can't be defaulted). Neither entry point knows how to migrate user data.
- **A non-rev-gated doc edit** (e.g. fixing a typo in an existing canonical doc without bumping the rev). `cps-init` will skip it.
- **A `cps.db` schema bump** (e.g. adding a new column to the chunks table). Requires a migration script, not a reinstall — Reinstall wipes data the user may still want.
- **A CLAUDE.md edit outside the fenced blocks** that needs to propagate across projects. `cps-init` does not touch content outside `cps-core BEGIN/END` fences.

For any of these, build a small dedicated skill with a one-paragraph charter and its own detection/write logic. Do not try to generalize it into a new patcher.

## Why not both (historical note)

Prior to 2026-04-11, CPS had a third entry point: `cps-patcher`, a skill that fetched a GitHub-hosted `Patches/patch-index.md` catalog and applied per-patch detection+write actions. It was retired on 2026-04-11 because every patch in the catalog (p001–p007) duplicated logic already implemented in `cps_scaffold.py`'s rev-gating. Maintaining both pipelines cost real authoring time and never produced a unique upgrade. Full retirement rationale: `Reference/Decisions/2026-04-11-cps-upgrade-model-two-entry-points.md`.
