---
name: cps-setup
description: >
  Canonical menu-driven installer for the Claude Project System (CPS). Deploys
  either CPS Core (scaffold + three pillars only) or CPS Full (Core + Python
  runtime + semantic search) into a target Cowork project. Supersedes
  cps-installer. Full installs auto-detect existing Core scaffolds and perform
  a graceful additive upgrade with no data migration. Triggers on: "cps-setup",
  "install cps", "set up cps", "deploy cps", "bootstrap cps", "install cps core",
  "install cps full", "upgrade cps to full", "add project brain", "set up
  knowledge base".
---

# cps-setup — Menu-Driven CPS Installer (rev 9)

> **Rev 9 (2026-04-10):** Step 6 and install-plan tables updated — cps-init now runs `cps_scaffold.py` via Python (not a cmd/ps1 script). No runtime changes.
> **Rev 8 (2026-04-10):** Step 1 `existing_core` detection + Step 5 validation + Step 6 cps-init writes updated to cover five buckets (Patterns, Decisions, Lessons, Ideas, Roadmap). No runtime changes.
> **Rev 7 (2026-04-09):** Rebundled `cps_server.py` and `cps_test_suite.py` — stripped Phase 7a/7b D3 baggage (engagement_id cache isolation, persona allowlists, PERSONA_BOOST). No schema migration needed; existing DBs silently retain the column.
> **Rev 6 (2026-04-09):** Removed Step 11 (.mcp.json wiring). CPS skills now call cps_server.py via subprocess CLI — no MCP server process required. Deleted mcp.json.template from Runtime/. Renumbered Steps 12–14 → 11–13.
> **Rev 5 (2026-04-09):** Rebundled `cps_server.py` from CPS rev 13 (self-heal fix: `_bootstrap_deps` now does verified re-import after pip and calls `sys.exit(1)` on failure — no more false `bootstrap complete`). Other 4 `.py` files unchanged.
> **Rev 4 (2026-04-09):** Rebundled all 5 Runtime `.py` files from CPS rev 13. Removes dead gear/complexity code from `cps_server.py` (`_compute_complexity`, `GEAR_THRESHOLDS`, gear surfacing in `cps_status`, complexity write-back at end of ingest). SKILL.md procedure unchanged.
> **Rev 3 (2026-04-09):** Added `py_compile` gate in Step 9 after line-count assertion.
> **Rev 2 (2026-04-08):** Rebundled `cps_server.py` and `cps_test_suite.py` from current Runtime rev 11. Removes Phase 8 stragglers (`cps_search_cross`, `ProjectRegistry`, namespace-prefixed chunk IDs). SKILL.md body unchanged.

This skill is the **only** install path for CPS. It deprecates `cps-installer`
and supersedes all previous install scaffolds (`cps-init`, `cps-platform`).

A successful run leaves the target project with either:

- **CPS Core** — scaffold + CLAUDE.md pointer sections + the three pillar skills
  (`cps-init`, `task`, `cps-capture`). No runtime, no semantic search. Grep and
  the 200-line TOC rule do retrieval. Ideal for projects under ~100 files.
- **CPS Full** — everything in Core, plus the Python runtime (`.cps/`,
  `cps_server.py`, `cps.db`), populated index, built knowledge
  graph, and the two query skills (`cps-query`, `cps-refresh`). Required when
  semantic search earns its keep — ~100+ files / ~10K+ markdown lines.

Full is a strict superset of Core. Graduation Core → Full is additive — no
migration, no schema change, no rewrites. See `Reference/CPS_Design.md` in the
CPS project for the full design rationale.

The installer **halts** before reporting success if any Full-path infrastructure
test fails.

## Bundled

`cps-query.skill`, `cps-refresh.skill`, and the 5 Python runtime modules
(`cps_server.py`, `cps_chunker.py`, `cps_embedder.py`, `cps_graph.py`,
`cps_test_suite.py`). All are Full-only — skipped entirely on Core installs.

**Not bundled:** `cps-init.skill`, `task.skill`, `cps-capture.skill`. These are
expected to already be installed globally (`~/.claude/skills/`) before running
cps-setup. If any are missing, Step 6 halts with instructions to install them
from the CPS project's `Skills/` folder first. Rationale: they are shared
skills owned by the CPS project itself and are presented/installed through the
normal Cowork skill flow, not bundled into every installer.

## Profile comparison

| Capability | Core | Full |
|---|---|---|
| Reference/ scaffold | ✅ | ✅ |
| CLAUDE.md §9/§11/§12 pointer sections | ✅ | ✅ |
| `task` skill (backlog) | ✅ | ✅ |
| `cps-capture` skill (second brain) | ✅ | ✅ |
| Semantic search | ❌ | ✅ |
| Knowledge graph | ❌ | ✅ |
| Python runtime + .cps/ | ❌ | ✅ |
| `cps-query` / `cps-refresh` | ❌ | ✅ |

## Step 1 — Pre-flight detection

`project_root` is the workspace folder Cowork is mounted on (NOT
`/sessions/...`). Determine current state:

- **existing_runtime** = `(project_root / ".cps" / "cps_config.json").exists()`
- **existing_core** = all three original buckets exist: `Reference/Patterns/_INDEX.md`,
  `Reference/Decisions/_INDEX.md`, `Reference/Lessons/_INDEX.md`
  (Ideas/Roadmap absence is tolerated for backward compat — Step 5 repairs them)

Record state for later branch logic. No prompts yet.

## Step 2 — Profile menu

Ask via `AskUserQuestion`:

> *"Which CPS profile do you want to install in this project?"*

Options:
- **Core** — scaffold + three pillars. No runtime. Recommended for projects
  under ~100 files.
- **Full** — Core + Python runtime + semantic search. Recommended for
  projects over ~100 files / ~10K markdown lines.
- **Upgrade Core → Full** — only show if `existing_core and not existing_runtime`.
  Skips Step 6 re-presentation of pillar skills (already installed), runs Core
  validation (Step 5), then jumps to Step 8.

If `existing_runtime` is already true, prompt:
**Upgrade runtime** (redeploy `.py` files, keep index, skip ingest) /
**Reinstall** (delete `cps.db`, `cps.db-journal`, `cps_manifest.json`, full
reindex) / **Cancel**. Branch accordingly and skip the profile menu.

Store selection as `profile ∈ {core, full, upgrade, reinstall}`.

## Step 3 — Prerequisites check

**Core:** no checks. Continue.

**Full (fresh or upgrade):** runs on **every** Full install — no skip-on-upgrade.

1. `python3 --version` → must be ≥ 3.10. Halt with install instructions if
   lower or missing.
2. Test write access: `Path(project_root / ".cps_preflight").touch()` then
   `unlink()`. Halt if PermissionError.
3. Test `pip` availability: `pip --version`. Halt if missing.

Report results and proceed only if all three pass.

## Step 4 — Install plan preview + approval gate

Show the user exactly what will happen, profile-aware. Example for Full:

```
CPS Full install plan:
  1. Validate Core scaffold (if present)
  2. Install cps-init.skill        [present via Cowork]
  3. Invoke cps-init               [runs cps_scaffold.py via Python — writes Reference/ scaffold + CLAUDE.md pointers]
  4. Install task.skill            [present via Cowork — skipped if already global]
  5. Install cps-capture.skill     [present via Cowork — skipped if already global]
  6. Install cps-query.skill       [present via Cowork — skipped if already global]
  7. Install cps-refresh.skill     [present via Cowork — skipped if already global]
  8. Deploy .cps/ runtime          [5 .py files, cps_config.json]
  9. Install dependencies          [sqlite-vec, onnxruntime, ...]
 10. Initial cps_ingest            [index source_paths]
 11. Build knowledge graph
 12. Run cps_test_suite.py         [halt on any fail]
 13. Summary
```

Example for Core (shorter):

```
CPS Core install plan:
  1. Install cps-init.skill        [present via Cowork]
  2. Invoke cps-init               [runs cps_scaffold.py via Python — writes Reference/ scaffold + CLAUDE.md pointers]
  3. Install task.skill            [present via Cowork — skipped if already global]
  4. Install cps-capture.skill     [present via Cowork — skipped if already global]
  5. Summary
```

Single `AskUserQuestion` approval gate: **Proceed** / **Cancel**. No partial
approvals, no mid-flight reprompts.

## Step 5 — Core validation (Full + Upgrade paths only)

Skip on Core installs.

When `profile == full` and `existing_core == True`, OR `profile == upgrade`,
validate the scaffold before proceeding to runtime:

```
checks = {
    # Required — halt if missing
    "Reference/Claude/":                                 is_dir,
    "Reference/Patterns/_INDEX.md":                      exists,
    "Reference/Decisions/_INDEX.md":                     exists,
    "Reference/Lessons/_INDEX.md":                       exists,
    "Reference/CPS_Task_Module.md":                      exists,
    "Reference/CPS_TOC_Rule.md":                         exists,
    "Reference/CPS_Capture_Taxonomy.md":                 exists,
    "CLAUDE.md §9 Task Module pointer":                  regex in CLAUDE.md,
    "CLAUDE.md §11 TOC Rule pointer":                    regex in CLAUDE.md,
    "CLAUDE.md §12 Capture Taxonomy pointer":            regex in CLAUDE.md,
    # Repairable — warn + create if missing (backward compat for pre-rev-8 installs)
    "Reference/Ideas/_INDEX.md":                         exists_or_repair,
    "Reference/Roadmap/_INDEX.md":                       exists_or_repair,
}
```

For **required** items: any miss → **halt**, report exact missing pieces, and offer:
**Fix with cps-init** / **Cancel**.

For **repairable** items (`exists_or_repair`): if missing, create the dir + write the
`_INDEX.md` stub inline (same content as cps-scaffold.ps1 `$IndexIdeas` / `$IndexRoadmap`)
without halting. Report as `REPAIRED` in the summary table.

User must approve the fix before Full install continues. Fresh Full installs
(no Core present) skip this step — Step 6 creates everything from scratch.

## Step 6 — Install pillar skills (cps-init + task + cps-capture)

Skip individual sub-steps on `profile == upgrade` (pillar skills already
installed per Step 2 precondition).

**Pre-check:** for each of `cps-init`, `task`, `cps-capture`, check
`~/.claude/skills/<name>/` or `~/.claude/skills/<name>.skill`. Skills already
installed globally are skipped silently (rev 7 pattern from cps-installer).

For each **not yet installed**: halt with instructions. cps-setup does NOT
bundle these — they live in the CPS source-of-truth project and are expected
to be installed globally by the user before running this installer. Example
halt message:

> *"cps-init.skill is not installed globally. Please install it from the CPS
> project's Skills/ directory first, then re-run cps-setup. Run `task ADD` on
> this gap if you want a tracking breadcrumb."*

Rationale: bundling would duplicate the same skill file into every CPS install
bundle and force a rev bump here every time any pillar skill changes. Global
install is the clean handoff.

**After cps-init is confirmed installed**, invoke it with the AskUserQuestion
flow or by surfacing its trigger phrase. cps-init runs the bundled
`cps_scaffold.py` via Python (Bash: `python cps_scaffold.py --target <path>`) — not the `.cmd` or `.ps1` files, which are Windows-only manual fallbacks.
cps-init writes:

- `Reference/Claude/` (empty, for `task` skill to populate)
- `Reference/Patterns/`, `Reference/Decisions/`, `Reference/Lessons/`,
  `Reference/Ideas/`, `Reference/Roadmap/` + `_INDEX.md` stubs for each
- `Reference/CPS_Task_Module.md`, `Reference/CPS_TOC_Rule.md`,
  `Reference/CPS_Capture_Taxonomy.md` (canonical reference docs)
- CLAUDE.md §9/§11/§12 pointer sections (per cps-init safety contract:
  existing files preserved, updated only if skill-embedded rev is newer)

Confirm cps-init completed successfully before continuing. If cps-init errored,
halt cps-setup.

## Step 7 — Core path termination

If `profile == core`, skip to Step 14 (summary). Everything beyond this point
is Full-only.

## Step 8 — Present Full-only skills (cps-query + cps-refresh)

Skip on `profile == core`.

Apply the rev 7 skip-if-installed pattern:

```python
from pathlib import Path

global_skills = Path.home() / ".claude" / "skills"
to_present = []
skipped    = []

for sub in ("cps-query", "cps-refresh"):
    if (global_skills / sub).exists():
        skipped.append(sub)
    else:
        to_present.append(skill_dir / f"{sub}.skill")
```

If `to_present` is empty, skip the `mcp__cowork__present_files` call entirely
and echo `"Both sub-skills already installed globally — skipping present step."`
If non-empty, present only those paths.

## Step 9 — Deploy Python runtime

Skip on `profile == core`.

Deploy these 5 modules from `skill_dir` to `project_root / ".cps/"`:
`cps_server.py`, `cps_chunker.py`, `cps_embedder.py`, `cps_graph.py`,
`cps_test_suite.py`.

**MUST use `Path.write_text()`, not `shutil.copy()` and not bash `cp`.**
shutil and bash both silently truncate large files on mounted folders. After
each write, read back and assert `written.count("\n") == src.count("\n").
Raise `RuntimeError` on mismatch — do not continue with a half-written runtime.

If the destination file exists and is read-only, `chmod(0o644)` it first; do
not delete-then-copy (changes the inode and breaks the running server's file
handle on self-hosting installs).

On `profile == reinstall`, first delete `cps.db`, `cps.db-journal`,
`cps_manifest.json` before deploying.

**py_compile gate (rev 3).** After all 5 files are written and line-count
asserted, compile each one in-process to catch corruption that line counts
miss (null bytes, truncation mid-statement, encoding damage):

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

This must halt the install before Step 10 if any file fails — a corrupted
runtime is unrecoverable downstream and a Step 12.5 test-suite failure
would be the first symptom otherwise.

## Step 10 — Collect source paths + generate config

Skip on `profile == core` and `profile == upgrade`.

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

`AskUserQuestion` (multiSelect) over the six candidates. Display rules:

- **Default-on** — path exists on disk AND is a markdown default
  (`Documentation/md/**/*.md`, `Reference/**/*.md`, or `Input/**/*.md`).
- **Default-off, shown** — path exists but isn't a markdown default
  (the `Source/` and `Reference/**/*.json` globs).
- **Suffixed `(not present — will skip)`** — path does not exist on disk.
  Default-off. Still selectable in case the user plans to create it before
  first ingest, but never default-on.

Allow custom paths via "Other".

Rationale: defaulting a non-existent path on (the pre-rev-7 behavior) caused
fresh installs to ingest 0 files when users accepted picker defaults without
reading them. As of CPS_Design.md rev 4 §4.2, `cps-init` scaffolds an empty
`Documentation/md/` so the default Full source path always resolves on fresh
installs. Disk-presence gating is kept in this step as belt-and-suspenders
defense for upgrade paths, custom source paths, and any project where
`cps-init` was an older rev that didn't scaffold `Documentation/`.

**Post-pick validation.** After the user picks, re-verify each selected path
exists:

- If the user explicitly chose a missing path (knowingly): warn once and
  proceed (they may create it before the first refresh).
- If every selected path is missing: halt with
  `"No selected source path exists on disk. Pick a path that exists or create
  one before re-running cps-setup."` Do not proceed to ingest a 0-file index.

Write `project_root / ".cps/cps_config.json"`:

```json
{
  "cps_dir": ".cps",
  "project_root": ".",
  "namespace": "<lowercase folder name, display label only>",
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

**Namespace** is a display label only (rev 11 of CPS removed chunk-ID
prefixing and cross-project search). Default to the lowercase, hyphenated
project folder name. Do not prompt unless the user asks to override.

**Do NOT include `auto_refresh_on_startup`** — removed in rev 11. Auto-refresh
is now driven by `cps_status.needs_refresh` (new files or large markdown
deltas) per `cps_server.py`.

Show config to user, confirm via `AskUserQuestion` (Proceed / Edit).

## Step 11 — Install dependencies (with import verifi