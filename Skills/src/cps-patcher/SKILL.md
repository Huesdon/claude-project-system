---
name: cps-patcher
description: Apply incremental CPS updates to an existing CPS-enabled project without a full reinstall. Use when CPS has released new features (new knowledge buckets, schema changes, scaffold updates, config changes) and you want to bring this project up to date. ALWAYS use this skill when the user says "patch cps", "update cps", "apply cps patch", "cps-patcher", "cps out of date", "bring cps up to date", "apply cps updates", or asks why their CPS project is missing features that a newer CPS version has.
---

# CPS Patcher (rev 3)

> **Rev 3 (2026-04-10):** Replaced the hardcoded `CATALOG_END p006-cps-core-block-rev3` sentinel with a dynamic sentinel check that parses the last table row from the catalog at runtime. Adding a new patch to `patch-index.md` no longer requires a skill rev bump — the sentinel just has to match the last row. Also unified on `mcp__github__get_file_contents` for all fetches (was split between WebFetch in the bundled rev 1 and GitHub MCP in the installed rev 2).

Apply incremental CPS updates to this project without a full reinstall.

## What it does

The patcher inspects the current project's CPS state, compares it against the known patch catalog, and applies any missing patches — creating directories, writing stub files, updating CLAUDE.md sections, patching canonical docs, and updating Full-profile config files. Each patch is idempotent: it re-checks live project state before applying and skips anything already present.

---

## Workflow

### Step 1 — Detect CPS profile

Check what CPS profile this project is running:
- **Full**: `.cps/cps_server.py` exists
- **Core**: `Reference/Claude/` exists but no `.cps/`
- **Unknown/None**: tell the user this doesn't appear to be a CPS project and stop

### Step 2 — Fetch and validate the patch index

Fetch the patch index via `mcp__github__get_file_contents`:

```
owner: Huesdon
repo: claude-project-system
path: Patches/patch-index.md
branch: main
```

**Dynamic sentinel check (mandatory).** The catalog is considered valid only if all of the following hold. If any check fails, abort immediately.

1. **Parse the patches table.** Find the markdown table with a header row containing `| ID |`. Collect every subsequent data row whose first column cell begins with `p` followed by a digit (e.g. `p001`, `p007`). Call the ID in the last such row `last_row_id`.
2. **Locate the sentinel.** Strip trailing whitespace and empty lines from the file. The final non-empty line must match this regex exactly: `^<!--\s*CATALOG_END\s+(?P<id>[A-Za-z0-9_\-]+)\s*-->$`. Extract the captured `id` as `sentinel_id`.
3. **Match.** Require `sentinel_id == last_row_id`.
4. **Table has at least one row.** Require `last_row_id` to be non-empty.

If any of the four checks fails, abort with:

> `ERROR: patch-index.md failed sentinel validation — last table row is '<last_row_id or NONE>' but CATALOG_END marker is '<sentinel_id or MISSING>'. Aborting to prevent silent partial patching.`

Do not proceed past this step if the sentinel check fails. This check guarantees (a) the file is not truncated mid-table and (b) whoever added the newest patch remembered to advance the sentinel. **Adding a new patch to the catalog never requires a skill rev bump** — the sentinel just has to match the last data row.

### Step 3 — Scan pending patches

For each patch in the index (in order):
1. Run the detection checks defined in the index against the current project state
2. Mark the patch as **needed** if any check fails, or **present** if all pass

Also read `Reference/Claude/cps_patch_manifest.json` if it exists — this is an audit log of previously applied patches. Use it as a hint but always re-check live state; the manifest is not authoritative.

### Step 4 — Show the plan and get approval

Present to the user:
- **Patches to apply**: name + one-line description for each needed patch
- **Already present**: patches whose checks all pass (skipping)
- Ask for explicit approval before touching any files

If nothing is needed, tell the user their project is up to date and stop.

### Step 5 — Apply patches (after approval)

For each pending patch, in index order:
1. Re-run detection (confirm still needed — skip if already present)
2. Fetch the patch file via `mcp__github__get_file_contents`:
   ```
   owner: Huesdon
   repo: claude-project-system
   path: Patches/patches/<file>
   branch: main
   ```
   where `<file>` is the filename from the index table for that patch.
3. Execute each action defined in the patch file
4. Report per-action outcome: **CREATED** / **UPDATED** / **SKIPPED**

Delegate file-write actions (creating dirs, writing stubs, editing files) to Haiku — pass the exact content from the patch file. Don't paraphrase or regenerate content; use what the patch file
