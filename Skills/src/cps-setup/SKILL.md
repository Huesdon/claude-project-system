---
name: cps-setup
description: >
  Canonical installer for the Claude Project System (CPS). Deploys either CPS
  Core (scaffold + three pillars, grep retrieval) or CPS Full (Core + Python
  runtime + semantic search + knowledge graph) into a target Cowork project
  folder. Handles fresh installs, Core→Full upgrades, runtime redeploys, and
  full reinstalls. Solo-developer, single-machine by design — assumes shared
  CPS skills are already installed globally at `/mnt/.claude/skills/`.
  Triggers on: "cps-setup", "install cps", "set up cps", "deploy cps",
  "bootstrap cps", "install cps core", "install cps full", "upgrade cps to
  full", "add project brain", "set up knowledge base".
---

# cps-setup — CPS Installer (rev 15)

> **Rev 15 (2026-04-11):** Step 3 prereq gate bumped from Python ≥3.10 to
> ≥3.11 to match the Step 10 `numpy==2.4.4` pin (numpy dropped 3.10 support
> in the 2.3 line). Added a Python-floor coupling note under the Step 10
> pin block so the gate and pin stay in sync on future edits. Found during
> a cps-setup test pass — gate accepted 3.10 but pip would have failed
> mid-install on the numpy wheel. Lesson:
> `Reference/Lessons/2026-04-11-cps-setup-numpy-python-floor.md`.
>
> **Rev 14 (2026-04-11):** Step 10 dependency install hardened. Rev 13 listed
> only the three top-level deps (`sqlite-vec huggingface-hub tokenizers`); pip
> resolved 18 transitive packages and the install hung mid-bootstrap on
> `onnxruntime` / `hf-xet` wheel fetch during a Full install at
> `H:\Claude Cowork\Projects\MSB`. Step 10 now installs the **full pinned
> 18-package set** with explicit versions, declares an expected duration
> (60–120s warm, 300s abort threshold), and warns that `onnxruntime` and
> `hf-xet` are the heavy fetches. Lesson: `Reference/Lessons/2026-04-11-cps-setup-step11a-dep-install.md`.
>
> **Rev 13 (2026-04-11):** Step 3 write-access probe hardened — locked filename
> to `.cps_preflight`, mandatory `try/finally` with `unlink(missing_ok=True)`,
> explicit "no improvisation" wording. New Step 12a stray-probe sweep removes
> any leftover `.cps_preflight` / `.cps_writetest` / `.cps_check` files at
> project root before printing the summary. Trigger: a Full install at
> H:\Claude Cowork\Projects\MSB left a `.cps_writetest` stray because Claude
> improvised the probe filename and skipped cleanup.
>
> **Rev 12 (2026-04-11):** Step 1 pillar-check now probes both the Cowork
> global path (`/mnt/.claude/skills/<name>/SKILL.md` or `.skill`) and the host
> global path (`~/.claude/skills/<name>/SKILL.md` or `.skill`), passing if the
> skill is present at either. Rev 11 only checked `~/.claude/skills/`, which
> Cowork does not populate — every Cowork install would halt at Step 1 with a
> false-negative pillar-missing error even when the pillars were correctly
> installed at `/mnt/.claude/skills/`. Step logic and downstream flow
> unchanged; probe path list only.
>
> **Rev 11 (2026-04-11):** Scope-correction and bundle repair. Reworded
> "single-tenant / one source-of-truth project" framing to the accurate
> solo-developer / single-machine / multi-project model: one developer
> (Shane), one machine, one global skill install at `/mnt/.claude/skills/`,
> **any number** of downstream Cowork project folders scaffolded from it.
> Repo canonicalized to `github.com/Huesdon/cowork-project-system` (old
> `claude-project-system` name retired). Rebundled from the GitHub source to
> restore Steps 11c and 12 that the previously installed bundle truncated
> mid–Step 11b. No step logic changed; wording and bundle integrity only.
>
> **Rev 10 (2026-04-11):** Full rewrite from first principles. All "bundle
> distribution" language removed. Pillar skills (`cps-init`, `task`,
> `cps-capture`, `cps-query`, `cps-refresh`) are assumed already installed
> globally under `/mnt/.claude/skills/`; missing pillars halt with an
> instruction to reinstall from the CPS source tree, not a bundle
> presentation. Steps renumbered and collapsed: 12 steps total, single linear
> flow with gates. Reconstructed Steps 11–12 that rev 6 truncated mid-heading.
>
> **Prior revs retained for history:** Rev 9 (Step 6 wording), Rev 8 (five
> buckets), Rev 7 (runtime rebundle), Rev 6 (MCP wiring removed), Rev 5
> (self-heal), Rev 4 (dead-gear removal), Rev 3 (py_compile gate), Rev 2
> (Phase 8 stragglers). Full history: `Reference/CPS_Phase_History.md`.

## Purpose

Deploy CPS into a target Cowork project folder. Two profiles:

- **CPS Core** — `Reference/` scaffold, canonical reference docs, CLAUDE.md
  §9/§11/§12 pointer sections. Grep and the §11 TOC rule do retrieval. Zero
  runtime, zero dependencies. Fits any project under ~100 markdown files.
- **CPS Full** — Core + `.cps/` Python runtime + SQLite semantic index +
  ONNX embeddings + knowledge graph. Required once the project outgrows grep
  (~100+ files / ~10K+ markdown lines). Adds ~5 MB of runtime plus the index.

Full is a strict superset of Core. Upgrading Core → Full is additive — no
migration, no schema change, no rewrites. Design rationale and profile details:
`Reference/CPS_Design.md` in the CPS source-of-truth project.

## Solo-developer assumption

CPS is a solo-developer, single-machine system. One developer (Shane), one
machine, one global skill install at `/mnt/.claude/skills/`, and any number
of Cowork project folders scaffolded from that single install. The CPS
source-of-truth repo lives at `github.com/Huesdon/cowork-project-system`.
The five CPS pillar skills (`cps-init`, `task`, `cps-capture`, `cps-query`,
`cps-refresh`) are installed once, globally, at `/mnt/.claude/skills/`. This
installer does not bundle, present, or install pillar skills — it assumes
they are already there. Step 1 verifies the assumption and halts if it fails.

## Bundled with this skill

The `.cps/` runtime files only: `cps_server.py`, `cps_chunker.py`,
`cps_embedder.py`, `cps_graph.py`, `cps_test_suite.py`. Deployed to
`project_root / .cps/` during Step 8. Full-only — Core installs skip the
deployment entirely.

## Profile comparison

| Capability | Core | Full |
|---|---|---|
| Reference/ scaffold | ✅ | ✅ |
| CLAUDE.md §9/§11/§12 pointer sections | ✅ | ✅ |
| `task` skill (backlog) | ✅ | ✅ |
| `cps-capture` skill (knowledge capture) | ✅ | ✅ |
| Semantic search | ❌ | ✅ |
| Knowledge graph | ❌ | ✅ |
| Python runtime + .cps/ | ❌ | ✅ |
| `cps-query` / `cps-refresh` | ❌ | ✅ |

---

## Step 1 — Pre-flight detection

Compute `project_root` — the mounted Cowork workspace folder (NOT any
`/sessions/...` path).

Probe current state:

- `existing_runtime` = `(project_root / ".cps/cps_config.json").exists()`
- `existing_core` = all three original buckets present:
  `Reference/Patterns/_INDEX.md`, `Reference/Decisions/_INDEX.md`,
  `Reference/Lessons/_INDEX.md`. Missing `Reference/Ideas/` or
  `Reference/Roadmap/` is tolerated — Step 7 repairs them.

Verify global pillar skills are installed. For each of `cps-init`, `task`,
`cps-capture`, `cps-query`, `cps-refresh`, probe **both** global skill roots:

- Cowork mount: `/mnt/.claude/skills/<name>/SKILL.md` OR `/mnt/.claude/skills/<name>.skill`
- Host home: `~/.claude/skills/<name>/SKILL.md` OR `~/.claude/skills/<name>.skill`

A pillar passes the check if it is present at **either** root. Cowork
sessions populate `/mnt/.claude/skills/` and leave `~/.claude/skills/` empty,
so probing only the host path produces a false-negative halt on every Cowork
install. If a pillar is absent from both roots, halt with:

> *"Pillar skill `<name>` is not installed globally. Reinstall it from
> `github.com/Huesdon/cowork-project-system/Skills/<name>.skill` first, then
> re-run cps-setup."*

Do not attempt to present or bundle a missing pillar. This is a
solo-developer system; the pillars are installed once and managed directly
in `/mnt/.claude/skills/`.

## Step 2 — Profile menu

Branch on detected state:

**If `existing_runtime == True`:** runtime already deployed. Present
`AskUserQuestion`:

- **Upgrade runtime** — redeploy `.cps/*.py`, keep index and config, skip
  ingest. Use when `Runtime/*.py` has drifted.
- **Reinstall** — delete `cps.db`, `cps.db-journal`, `cps_manifest.json`, then
  full redeploy + full reindex. Use when the index is corrupted or a schema
  change landed.
- **Cancel** — no-op.

Store as `profile ∈ {upgrade_runtime, reinstall}`. Skip the fresh-install menu.

**If `existing_runtime == False`:** present `AskUserQuestion`:

- **Core** — scaffold + three pillars. No runtime. Recommended for projects
  under ~100 files.
- **Full** — Core + Python runtime + semantic search. Recommended for
  projects over ~100 files / ~10K markdown lines.
- **Upgrade Core → Full** — only offer if `existing_core == True`. Runs
  validation + deploys runtime, skips the scaffold rewrite.

Store as `profile ∈ {core, full, upgrade_core_to_full}`.

## Step 3 — Prerequisites check

**Core-only installs:** no checks. Continue.

**Any Full-path profile** (`full`, `upgrade_core_to_full`, `upgrade_runtime`,
`reinstall`): run every time — no skip-on-upgrade.

1. `python3 --version` → must be ≥ 3.11. Halt with install instructions if
   lower or missing. (Gate is 3.11, not 3.10, because the pinned `numpy==2.4.4`
   below dropped Python 3.10 support in the 2.3 line. Keep the gate and the
   numpy pin in sync — if you ever relax numpy to 2.2.x, drop the gate back
   to 3.10 in the same edit.)
2. Test write access — **use this exact pattern, no improvisation**:

   ```python
   from pathlib import Path
   probe = project_root / ".cps_preflight"
   try:
       probe.touch()
   except PermissionError:
       halt("write access denied at project_root")
   finally:
       probe.unlink(missing_ok=True)
   ```

   Filename is locked to `.cps_preflight`. Do not invent alternates
   (`.cps_writetest`, `.cps_check`, etc.). The `finally` clause is mandatory
   so a halt-on-touch still cleans up if the touch ever partially succeeds.
3. Test `pip` availability: `pip --version`. Halt if missing.

Report results inline and proceed only if all three pass.

## Step 4 — Install plan preview + approval

Show the user exactly what will happen, profile-aware. Example for Full:

```
CPS Full install plan:
  1. Invoke cps-init               [writes Reference/ scaffold + CLAUDE.md pointers]
  2. Validate Core scaffold        [five buckets + CLAUDE.md pointer sections]
  3. Deploy .cps/ runtime          [5 .py files, verified with py_compile]
  4. Collect source paths          [AskUserQuestion multiSelect]
  5. Write cps_config.json
  6. Install pip dependencies      [18 pinned wheels — see Step 10, ~60–120s]
  7. Initial cps_ingest            [index source_paths]
  8. Build knowledge graph
  9. Run cps_test_suite.py         [halt on any fail]
 10. Summary
```

Example for Core:

```
CPS Core install plan:
  1. Invoke cps-init               [writes Reference/ scaffold + CLAUDE.md pointers]
  2. Summary
```

Example for `upgrade_runtime`:

```
CPS runtime upgrade plan:
  1. Deploy .cps/ runtime          [5 .py files, verified with py_compile]
  2. Install pip dependencies      [18 pinned wheels — imports re-verified]
  3. Run cps_test_suite.py         [halt on any fail]
  4. Summary
```

Single `AskUserQuestion` gate: **Proceed** / **Cancel**. One approval, no
mid-flight re-prompts.

## Step 5 — Invoke cps-init (scaffold)

Skip on `profile ∈ {upgrade_runtime, reinstall}` (scaffold already present).

Invoke the globally-installed `cps-init` skill against `project_root`.
cps-init runs `cps_scaffold.py` via Python and writes:

- `Reference/Claude/` (empty, populated later by the `task` skill)
- Five bucket dirs with `_INDEX.md` stubs: `Reference/Patterns/`,
  `Reference/Decisions/`, `Reference/Lessons/`, `Reference/Ideas/`,
  `Reference/Roadmap/`
- Canonical reference docs: `Reference/CPS_Task_Module.md`,
  `Reference/CPS_TOC_Rule.md`, `Reference/CPS_Capture_Taxonomy.md`
- CLAUDE.md §9 (Task Module), §11 (TOC Rule), §12 (Capture Taxonomy) pointer
  sections. cps-init preserves existing CLAUDE.md content and updates section
  blocks only when the skill-embedded rev is newer than the on-disk rev.

cps-init is idempotent — safe to invoke on an already-scaffolded project.

Halt cps-setup if cps-init errors. Do not continue with a half-written
scaffold.

## Step 6 — Core path termination

If `profile == core`, skip to Step 12 (Summary). Everything beyond this point
is Full-only.

## Step 7 — Core validation (Full-path only)

Skip on `profile == core`.

When `existing_core == True` (fresh Full install against an existing Core
scaffold, or any upgrade path), validate the scaffold before touching the
runtime:

```
required = {
    "Reference/Claude/":                                is_dir,
    "Reference/Patterns/_INDEX.md":                     exists,
    "Reference/Decisions/_INDEX.md":                    exists,
    "Reference/Lessons/_INDEX.md":                      exists,
    "Reference/CPS_Task_Module.md":                     exists,
    "Reference/CPS_TOC_Rule.md":                        exists,
    "Reference/CPS_Capture_Taxonomy.md":                exists,
    "CLAUDE.md §9 Task Module pointer":                 regex in CLAUDE.md,
    "CLAUDE.md §11 TOC Rule pointer":                   regex in CLAUDE.md,
    "CLAUDE.md §12 Capture Taxonomy pointer":           regex in CLAUDE.md,
}
repairable = {
    "Reference/Ideas/_INDEX.md":                        exists_or_repair,
    "Reference/Roadmap/_INDEX.md":                      exists_or_repair,
}
```

**Required items:** any miss → halt, report exact missing pieces, offer
**Fix with cps-init** / **Cancel** via `AskUserQuestion`. "Fix with cps-init"
re-invokes Step 5 then re-runs this validation.

**Repairable items:** if missing, create the dir and write the `_INDEX.md`
stub inline (same content as `cps_scaffold.py` emits). Do not halt. Report as
`REPAIRED` in the Step 12 summary table.

Fresh Full installs against an empty project (no `existing_core`) skip this
step — Step 5 already created everything from scratch.

## Step 8 — Deploy Python runtime

Skip on `profile == core`.

Deploy these 5 modules from `skill_dir` to `project_root / ".cps/"`:
`cps_server.py`, `cps_chunker.py`, `cps_embedder.py`, `cps_graph.py`,
`cps_test_suite.py`.

**Use `Path.write_text()`, not `shutil.copy()` and not bash `cp`.** Both shutil
and bash silently truncate large files on Cowork FUSE mounts. After each
write, read back and assert `written.count("\n") == src.count("\n")`. Raise
`RuntimeError` on mismatch — do not continue with a half-written runtime.

If the destination file exists and is read-only, `chmod(0o644)` it first. Do
not delete-then-copy — changing the inode breaks any running server's file
handle on self-hosting installs.

On `profile == reinstall`, first delete `cps.db`, `cps.db-journal`, and
`cps_manifest.json` before deploying.

**py_compile gate.** After all 5 files are written and line-count asserted,
compile each in-process to catch corruption that line counts miss (null bytes,
truncation mid-statement, encoding damage):

```python
import py_compile
runtime_files = ["cps_server.py", "cps_chunker.py", "cps_embedder.py",
                 "cps_graph.py", "cps_test_suite.py"]
for f in runtime_files:
    try:
        py_compile.compile(str(cps_dir / f), doraise=True)
    except py_compile.PyCompileError as e:
        raise RuntimeError(f"Deployed {f} failed py_compile: {e}")
```

Halt the install before Step 9 if any file fails — a corrupted runtime is
unrecoverable downstream, and a Step 11 test-suite failure would be the first
symptom otherwise.

## Step 9 — Collect source paths + write config

Skip on `profile ∈ {upgrade_runtime, reinstall}` (config already present).

**Disk-presence check first.** Before showing the picker, probe each candidate
path under `project_root`:

```python
candidates = [
    ("Documentation/md/**/*.md", "Documentation/md"),
    ("Reference/**/*.md",        "Reference"),
    ("Input/**/*.md",            "Input"),
    ("Source/**/*.py",           "Source"),
    ("Source/**/*.js",           "Source"),
    ("Reference/**/*.json",      "Reference"),
]
present = {glob: (project_root / dirpath).is_dir() for glob, dirpath in candidates}
```

Present `AskUserQuestion` (multiSelect) over the six candidates. Display rules:

- **Default-on** — path exists on disk AND is a markdown default
  (`Documentation/md/**/*.md`, `Reference/**/*.md`, or `Input/**/*.md`).
- **Default-off, shown** — path exists but isn't a markdown default
  (the `Source/` and `Reference/**/*.json` globs).
- **Suffixed `(not present — will skip)`** — path does not exist on disk.
  Default-off. Still selectable in case the user plans to create it before
  first ingest, but never default-on.

Allow custom paths via the question's "Other" option.

Rationale: defaulting a non-existent path on (pre-rev-7 behavior) caused fresh
installs to ingest 0 files when users accepted picker defaults without reading
them. As of CPS_Design.md rev 4 §4.2, `cps-init` scaffolds an empty
`Documentation/md/` so the default Full source path always resolves. The
disk-presence gate here is belt-and-suspenders defense for upgrade paths,
custom source paths, and older `cps-init` revs that didn't scaffold
`Documentation/`.

**Post-pick validation.** After the user picks, re-verify each selected path:

- If the user knowingly chose a missing path: warn once and proceed (they may
  create it before the first refresh).
- If every selected path is missing: halt with *"No selected source path
  exists on disk. Pick a path that exists or create one before re-running
  cps-setup."* Do not proceed to ingest a 0-file index.

Write `project_root / ".cps/cps_config.json"`:

```json
{
  "cps_dir": ".cps",
  "project_root": ".",
  "namespace": "<lowercase hyphenated folder name>",
  "source_paths": ["<from prompt>"],
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_dim": 384,
  "chunk_min_tokens": 50,
  "chunk_max_tokens": 2000,
  "search_default_limit": 5,
  "cache": {"similarity_threshold": 0.05, "max_age_hours": 24}
}
```

**`cps_dir` and `project_root` MUST be relative.** Absolute paths embed the
session ID and break on every new Cowork conversation.

**Namespace** is a display label only — chunk-ID prefixing and cross-project
search were removed in CPS rev 11. Default to the lowercase, hyphenated
project folder name. Do not prompt unless the user asks to override.

**Do NOT include `auto_refresh_on_startup`** — removed in rev 11. Auto-refresh
is now driven by `cps_status.needs_refresh` (new files or large markdown
deltas).

Show config to user, confirm via `AskUserQuestion` (**Proceed** / **Edit**).
On Edit, re-run the picker.

## Step 10 — Install dependencies (with import verification)

Skip on `profile == core`.

Install the **full pinned dependency set**. Rev 13 and earlier listed only the
three top-level intent packages (`sqlite-vec huggingface-hub tokenizers`) and
let pip resolve transitives non-deterministically. That produced an 18-package
transitive resolution, and a Full install at `H:\Claude Cowork\Projects\MSB`
hung mid-bootstrap on the `onnxruntime` / `hf-xet` wheel fetch with no signal
to the operator about which wheel was stalled. Pinning eliminates the
non-determinism and tells the operator the exact surface area:

```bash
pip install --break-system-packages \
  sqlite-vec \
  annotated-doc==0.0.4 \
  click==8.3.2 \
  filelock==3.25.2 \
  fsspec==2026.3.0 \
  hf-xet==1.4.3 \
  huggingface-hub==1.10.1 \
  markdown-it-py==4.0.0 \
  mdurl==0.1.2 \
  numpy==2.4.4 \
  onnxruntime==1.24.4 \
  packaging==26.0 \
  protobuf==7.34.1 \
  pygments==2.20.0 \
  pyyaml==6.0.3 \
  rich==14.3.4 \
  shellingham==1.5.4 \
  tokenizers==0.22.2 \
  typer==0.24.1
```

**Expected duration:** 60–120s on a warm pip cache / fast network. **Abort
threshold:** 300s. If the install has not completed in five minutes, it is
stalled — almost always on `onnxruntime` (≈100 MB wheel) or `hf-xet` (model
registry probe). Cancel the subprocess, clear pip cache (`pip cache purge`),
and re-run. Pre-warm pip cache before deploying CPS Full to a cold machine.

`sqlite-vec` is intentionally unpinned — its release cadence is fast and the
ABI is stable. Every other package is pinned because `numpy` 3.x or
`onnxruntime` major bumps will silently break the runtime.

**Python floor coupling:** `numpy==2.4.4` requires Python ≥ 3.11 (numpy
dropped 3.10 support in the 2.3 line). The Step 3 prereq gate is held at
≥ 3.11 to match. If you ever relax numpy to a 2.2.x pin, drop the gate
back to 3.10 in the same edit.

**After the install, verify imports in a subprocess** to confirm the wheels
landed and are loadable. A successful `pip install` return code is not
sufficient — silent ABI mismatches produce "installed but import fails"
failures that only surface mid-ingest:

```python
import subprocess, sys
verify_script = (
    "import sqlite_vec, huggingface_hub, tokenizers, "
    "numpy, onnxruntime; print('ok')"
)
result = subprocess.run(
    [sys.executable, "-c", verify_script],
    capture_output=True, text=True
)
if result.returncode != 0 or "ok" not in result.stdout:
    raise RuntimeError(
        f"Dependency import verification failed:\n{result.stderr}"
    )
```

Halt the install on any import failure. Report the failing module inline.

On `profile == upgrade_runtime`, the install step is still run — pip is a
no-op when packages are already at the right version, and the import
verification catches any post-upgrade ABI drift.

## Step 11 — Initial ingest + graph build + test suite

Skip on `profile == core`.

Run the three-phase Full-path validation. Any phase failure halts the install
before Step 12 — a failed install must not report success.

### 11a — Initial ingest

Invoke:

```bash
python .cps/cps_server.py ingest
```

from `project_root`. The subprocess discovers `source_paths` from
`cps_config.json`, chunks every matching file, embeds each chunk, and writes
to `cps.db`.

Capture and parse the JSON response. Required fields:

- `files_indexed` > 0 (unless the project is genuinely empty — warn, do not
  halt, if the user chose an empty source path knowingly)
- `chunks_written` > 0 on any non-zero `files_indexed`
- `errors` is empty or absent

Halt on any parse failure, non-zero exit code, or populated `errors` field.

### 11b — Build knowledge graph

Invoke:

```bash
python .cps/cps_server.py graph_build
```

Capture the response. Required: `nodes > 0`, `edges >= 0`, `errors` empty.
Halt on failure.

### 11c — Test suite

Invoke:

```bash
python .cps/cps_test_suite.py
```

The test suite self-bootstraps its deps (sqlite-vec, huggingface-hub,
tokenizers, onnxruntime, numpy) via `_bootstrap_deps()` and exercises every
MCP tool surface: `cps_search`, `cps_retrieve`, `cps_status`, `cps_ingest`,
`cps_prime`, `cps_purge`, `cps_graph_build`, `cps_graph_query`.

Require exit code 0. Any non-zero exit halts the install with the test
suite's stderr reported inline. Do not proceed to the summary on a failing
test suite — that was the whole point of the gate.

On `profile == upgrade_runtime`, 11a is still run so the test suite exercises
the ingest pipeline end-to-end against the redeployed runtime. This is the
only way to verify the self-hosting `sync_runtime_to_cps()` hook is working.

## Step 12 — Stray-probe sweep + summary

### 12a — Stray-probe sweep

Scan `project_root` for any leftover preflight probe files and remove them.
Catches the case where a previous run (this skill or any earlier rev) created
a probe and never cleaned it up.

```python
for stray in project_root.glob(".cps_*"):
    if stray.is_file() and stray.name in {".cps_preflight", ".cps_writetest", ".cps_check"}:
        stray.unlink()
```

Do not glob-delete `.cps_*` indiscriminately — `.cps/` is the runtime directory
and must be preserved. The allowlist above is exhaustive: extend it if a future
rev adds another probe filename.

### 12b — Summary

Print a single compact report. Profile-aware. Example for a clean Full install:

```
╭─ CPS Full install complete ─────────────────────────────────
│ profile:          full
│ project_root:     /mnt/<folder>
│ scaffold:         OK        (5 buckets, 3 reference docs)
│ runtime:          OK        (5 .py files, py_compile clean)
│ config:           OK        (source_paths: Documentation/md, Reference)
│ dependencies:     OK        (18 pinned wheels, imports verified)
│ ingest:           OK        (N files, M chunks, K tokens)
│ graph:            OK        (X nodes, Y edges)
│ test suite:       OK        (Z tests passed)
╰──────────────────────────────────────────────────────────────

Next steps:
  • Run `cps-query` to search the index.
  • Run `cps-refresh` after any doc edits.
  • Run `cps-capture` to add patterns/decisions/lessons/ideas/roadmap items.
```

For Core:

```
╭─ CPS Core install complete ─────────────────────────────────
│ profile:          core
│ project_root:     /mnt/<folder>
│ scaffold:         OK        (5 buckets, 3 reference docs)
│ CLAUDE.md:        OK        (§9, §11, §12 pointer sections)
╰──────────────────────────────────────────────────────────────

Next steps:
  • Use grep + the §11 TOC rule for retrieval.
  • Run `task` to manage the backlog.
  • Run `cps-capture` to add patterns/decisions/lessons/ideas/roadmap items.
  • Re-run `cps-setup` and choose "Upgrade Core → Full" when the project
    crosses ~100 files.
```

For upgrade paths, list only the steps that ran and their results. Flag any
`REPAIRED` items from Step 7 in a dedicated row.

The summary is the only success signal. If Step 11 halted, the summary never
prints — the user sees the halt reason and resolves it before re-running.

---

## Error recovery

Every halt in this skill is recoverable. The halts are:

| Halt point | Recovery |
|---|---|
| Step 1 missing pillar skill | Reinstall the named skill from the CPS source tree, re-run cps-setup |
| Step 3 python/pip/write-access | Fix the environment issue, re-run cps-setup |
| Step 5 cps-init error | Read the cps-init error, fix the project state, re-run cps-setup |
| Step 7 required item missing | Pick "Fix with cps-init" to re-scaffold |
| Step 8 `py_compile` failure | The runtime source is corrupted upstream — re-fetch from GitHub, rebundle, reinstall cps-setup itself |
| Step 9 all source paths missing | Create at least one source directory, re-run cps-setup |
| Step 10 install hang (>300s) | Cancel, `pip cache purge`, pre-warm `onnxruntime` + `hf-xet` wheels, re-run |
| Step 10 import verification failure | Check pip output, clear pip cache if needed, re-run cps-setup |
| Step 11a/11b/11c failure | Read the reported error — likely a runtime bug, file an issue in the CPS source-of-truth project |

The installer is idempotent. Re-running after a halt resumes from Step 1 and
re-detects state. Completed phases (scaffold present, runtime deployed) are
skipped via the branch logic in Step 2 and the per-step skip conditions.
