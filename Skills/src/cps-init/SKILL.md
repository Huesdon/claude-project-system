---
name: cps-init
description: Canonical CPS scaffolder. Creates the Reference/ tree, canonical reference docs, CLAUDE.md §9/§11/§12 pointer sections, and (optionally) the Full profile block in a target Cowork project via cps_scaffold.py fetched from GitHub main at runtime. Idempotent — safe to re-run. Triggers on "cps-init", "scaffold cps", "initialize cps project", "set up cps reference folders", "create cps scaffold".
---

# cps-init — CPS Scaffolder (rev 3)

> **Rev 3 (2026-04-10):** No longer bundles `cps_scaffold.py`. Fetches it from `raw.githubusercontent.com/Huesdon/claude-project-system/main/Reference/cps_scaffold.py` at runtime, same pattern as `cps-patcher`'s catalog fetch. Removes the "rebundle cps-init.skill on scaffold edit" house rule — scaffold edits now propagate via `git push` to main. Previous rev bundled a 600-line copy of the scaffolder that required rebundling on every edit.
>
> **Rev 2 (2026-04-10):** Rewrote as a real scaffolder. Bundled `cps_scaffold.py` (Python port of `cps-scaffold.ps1`) which Claude invoked via Bash.

## What this skill does

Creates the CPS scaffold in a target project by fetching and running the canonical Python scaffolder from GitHub:

1. Folder tree: `Reference/{Claude,Patterns,Decisions,Lessons,Ideas,Roadmap}`, `Documentation/md/`, `Input/`, `Output/`.
2. `_INDEX.md` stubs for each `Reference/` bucket.
3. Canonical reference docs with rev-aware upgrade logic:
   - `Reference/CPS_Task_Module.md`
   - `Reference/CPS_TOC_Rule.md`
   - `Reference/CPS_Capture_Taxonomy.md`
4. `CLAUDE.md` block injection (rev-aware): `cps-core` block always, `cps-full` block if profile is `full`.

Everything is idempotent. Re-runs skip existing files with matching rev markers, upgrade older revs, and create anything missing. Safe to run on an already-scaffolded project.

## Bundle contents

This skill bundles **only `SKILL.md`**. The scaffolder is fetched at runtime from:

```
https://raw.githubusercontent.com/Huesdon/claude-project-system/main/Reference/cps_scaffold.py
```

The `.ps1`/`.cmd` Windows standalone fallbacks are no longer bundled. Users who want to scaffold manually outside of Cowork can download them directly from the GitHub repo at the same path.

## Procedure

### Step 1 — Idempotency check

Verify whether the target project is already scaffolded by checking for all three:
- `CLAUDE.md` at project root
- `Reference/` directory
- All three canonical docs: `Reference/CPS_Task_Module.md`, `Reference/CPS_TOC_Rule.md`, `Reference/CPS_Capture_Taxonomy.md`

If all three conditions are true AND this skill was invoked standalone (not from `cps-setup` Step 5/6): one-line confirm — *"CPS scaffold detected — project is initialized."* Then ask via `AskUserQuestion` whether to re-run for rev upgrades. If invoked by `cps-setup`, proceed to re-run automatically (it handles gaps and rev upgrades).

### Step 2 — Determine target path

Default target is the Cowork project root — the mounted folder the user selected at session start. If the user is working in a subdirectory or there's ambiguity, use `AskUserQuestion` to confirm the target path before proceeding.

### Step 3 — Determine profile

If not supplied by the caller, ask via `AskUserQuestion`:
- **CPS Core** — scaffold + three pillars, no Python runtime. Recommended for projects under ~100 files.
- **CPS Full** — Core + Python runtime + semantic search. Requires a `cps-setup` follow-up to deploy the runtime.

If invoked by `cps-setup` (which already knows the profile), accept the profile hint and skip this prompt.

### Step 4 — Fetch the scaffolder from GitHub

Create a temp directory and fetch `cps_scaffold.py` via `curl` (bytes are preserved verbatim — do not use `WebFetch`, which passes content through an LLM and corrupts raw Python source).

```bash
TMPDIR=$(mktemp -d -t cps-init-XXXXXX)
curl -fsSL "https://raw.githubusercontent.com/Huesdon/claude-project-system/main/Reference/cps_scaffold.py" -o "$TMPDIR/cps_scaffold.py"
```

**Sanity checks (mandatory) — abort if any fail:**

1. File exists and is non-empty (`[ -s "$TMPDIR/cps_scaffold.py" ]`).
2. First line is `#!/usr/bin/env python3`.
3. Contains the literal string `CPS scaffold — Python port of cps-scaffold.ps1` (the module docstring marker).
4. Contains `def main() -> int` (the entrypoint).
5. Size is at least 10,000 bytes (catches truncated fetches — the real file is ~24KB).

If any check fails, halt with: *"ERROR: fetched cps_scaffold.py failed sanity check — aborting to prevent scaffolding from a corrupted or truncated file. Check network connectivity and the GitHub source at `https://github.com/Huesdon/claude-project-system/blob/main/Reference/cps_scaffold.py`.*

Sample combined check (bash):

```bash
python3 -c "
import sys, pathlib
p = pathlib.Path('$TMPDIR/cps_scaffold.py')
if not p.exists() or p.stat().st_size < 10000:
    sys.exit('missing or too small')
head = p.read_text(encoding='utf-8').splitlines()
if head[0] != '#!/usr/bin/env python3':
    sys.exit('shebang missing')
body = p.read_text(encoding='utf-8')
if 'CPS scaffold — Python port of cps-scaffold.ps1' not in body:
    sys.exit('docstring marker missing')
if 'def main() -> int' not in body:
    sys.exit('main() missing')
print('ok')
"
```

### Step 5 — Execute the scaffolder

Invoke the fetched scaffolder via Bash:

```bash
python3 "$TMPDIR/cps_scaffold.py" --path "<target>" --profile <core|full>
```

The scaffolder prints an outcome table + summary to stdout and exits 0 on success, non-zero on failure.

### Step 6 — Report outcome

Surface the outcome table and summary line to the user. If profile is `full`, remind the user that the next step is to run `cps-setup` to deploy the Python runtime and build the semantic index.

If the scaffolder exited non-zero, surface the error and halt. Do NOT attempt to fix issues inline — the Python scaffolder is the single source of truth and any drift must be fixed at `Reference/cps_scaffold.py` in the CPS source-of-truth project, then committed and pushed to GitHub main.

## Do not

- Do not use `WebFetch` to retrieve `cps_scaffold.py`. `WebFetch` processes content through an LLM and will corrupt raw Python source. Always use Bash + `curl` for byte-exact transfer.
- Do not reimplement scaffolding inline via Write/Edit tool calls or bash file writes. `cps_scaffold.py` fetched from GitHub main is the single source of truth.
- Do not fall back to a cached or local copy if the fetch fails. Halt and surface the error — silent fallback would mask GitHub drift and defeat the purpose of runtime fetching.
- Do not edit or save the fetched `cps_scaffold.py` back anywhere. It lives in `$TMPDIR` for the duration of this invocation and is discarded afterward. Canonical edits happen in the CPS source-of-truth project at `Reference/cps_scaffold.py` followed by `git push`.
- Do not tell users to download or double-click the Windows `.cmd`/`.ps1` files. Those are manual-fallback convenience artifacts on GitHub for users outside Cowork, not part of this skill's flow.

## Contract for programmatic callers (e.g. `cps-setup` Step 6)

When another skill invokes this one by trigger phrase:

1. **Inputs required:** target path, profile (`core` or `full`).
2. **Outputs:** the outcome table printed by `cps_scaffold.py` and a success/failure status.
3. **Failure mode:** non-zero exit from `cps_scaffold.py` — or a failed sanity check in Step 4 — propagates up. The caller should halt and surface the error.
4. **Idempotency guarantee:** re-runs on an already-scaffolded project are safe and produce a `SKIPPED` outcome table. Callers do not need to pre-check scaffold state.
5. **Network requirement:** this skill now requires outbound HTTPS to `raw.githubusercontent.com`. Offline environments will fail at Step 4. There is no bundled fallback by design.