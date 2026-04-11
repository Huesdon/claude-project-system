#!/usr/bin/env python3
"""
CPS scaffold — Python port of cps-scaffold.ps1. Creates CPS Core or Full folder
structure in the target project. Idempotent — safe to re-run; existing non-empty
files are preserved.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import re
import os

# --------------------------------------------------------------------------
# Embedded template revs (match cps-init templates/ as of 2026-04-09)
# --------------------------------------------------------------------------
TASK_MODULE_REV = 2
TOC_RULE_REV = 1
CAPTURE_REV = 2
CORE_SECTION_REV = 4
FULL_SECTION_REV = 2

# --------------------------------------------------------------------------
# Embedded templates (triple-quoted = verbatim, no interpolation)
# --------------------------------------------------------------------------

INDEX_PATTERNS = """# Patterns Index

Entries added by `cps-capture` as reusable techniques and design approaches accumulate.
"""

INDEX_DECISIONS = """# Decisions Index

Entries added by `cps-capture` as design decisions (with context and rationale) accumulate.
"""

INDEX_LESSONS = """# Lessons Index

Entries added by `cps-capture` as gotchas and hard-won lessons accumulate.
"""

INDEX_IDEAS = """# Ideas Index

Nascent ideas, exploration candidates, and "what if" items. Capture early, promote when ready.
Use `cps-capture` with trigger "add idea". Promote to Roadmap with "promote [title] to roadmap".

<!-- entries below -->
"""

INDEX_ROADMAP = """# Roadmap Index

Committed intentions, not yet active tasks. Each item has a goal, rationale, and horizon (Now/Next/Later).
Use `cps-capture` with trigger "add to roadmap". Promote to tasks with "promote [title] to tasks".

<!-- entries below -->
"""

TASK_MODULE = """<!-- rev: 2 -->
# CPS Task Module — Backlog Management Standard

> Externalized from CLAUDE.md §9 on 2026-04-08 to reduce per-session token cost. CLAUDE.md retains the trigger summary; this file holds the full rationale and detail.
>
> **Applies to:** Any CPS-enabled project that uses the `task` skill for cross-session backlog management. This is the standard scaffold installed by the `task` skill on first run. Do not edit individual rules without updating the skill.

## 1. Session Start — RECOMMEND Flow

At session start, read `Reference/Claude/tasks.json` (active T1/T2 only) and surface the top 1–3 tasks as an `AskUserQuestion` before any other work begins. Do **NOT** read `tasks_backlog.json` at startup — it contains deferred work. Trust the existing order: REPRIORITIZE produces a dependency-aware ranking, so the top of the file is already the right answer. Wait for user confirmation before starting. Be concise and do not echo your instructions, just do them.

## 2. Suggested Session Boundary on Task Completion

When a backlog task is fully complete — all file updates done, `tasks.json` updated via `task COMPLETE`, and any related docs propagated — Claude should suggest closing the session and starting the next task in a fresh conversation. This is a recommendation, not a hard stop. Small or tightly-related tasks may be batched in one session at the user's discretion.

**What counts as "task complete":** All steps finished, `tasks.json` updated, and any required doc updates propagated. Not "mostly done."

## 3. Task Cleanup Before Session Close (MANDATORY)

Before ending any session, call `task COMPLETE` on every item finished. Completed tasks are removed from `tasks.json` and appended as a single line to `Reference/Claude/tasks_completed.log` (format: `YYYY-MM-DD | task-id | title`). Do not leave checkmark stubs or strikethrough entries in `tasks.json` — they burn tokens on every future RECOMMEND pass. The log preserves history without bloating the active backlog.

## 4. Reprioritization Counter

`tasks.json` header tracks `completions_since_reprioritization`. On every `task COMPLETE` call, increment this counter. When it reaches **10**, prompt the user:

> *"10 tasks completed since the last reprioritization — want me to run REPRIORITIZE now?"*

If confirmed, run a full `task REPRIORITIZE` pass (dependency-first, all tiers) and reset the counter to 0. If declined, leave the counter and re-prompt at the next completion. This keeps backlog priorities honest without surprise mid-session reprioritizations.

The threshold defaults to 10 but is configurable per project via the `reprioritize_threshold` field in the `tasks.json` meta header.

## 5. Keep tasks.json Current

`Reference/Claude/tasks.json` is the cross-session task backlog and the single source of truth. When new work is discovered mid-session — either by Claude noticing a follow-up or by the user mentioning something — call `task ADD` immediately rather than mentioning it in chat and forgetting. Treat user-added entries as authoritative: do not second-guess priority, retitle, or reorder them without explicit instruction.

## 6. Propagate Design Changes to Documentation Same-Session

After any design decision or architectural change, update all relevant `Reference/*.md` and `Documentation/md/*.md` files in the same session. Create a new Reference doc if none exists for the topic. Do not close a session with design decisions captured only in `tasks.json` or session memory — they must be fully encoded in documentation files.

CPS indexes these docs; stale docs mean stale query results, which defeats the purpose of the knowledge layer. **After doc updates, run `cps-refresh` to re-index changed files before session close.**
"""

TOC_RULE = """<!-- rev: 1 -->
# CPS TOC Maintenance Rule (MANDATORY)

> Externalized from CLAUDE.md §11 on 2026-04-08 to reduce per-session token cost. CLAUDE.md retains a one-line summary pointing at this file.

Every `Reference/` or `Documentation/md/` file that exceeds **200 lines** must have a companion `_TOC.md` file. The TOC lists every `##` and `###` heading with its line number in a two-column markdown table (`Line | Section`). This enables targeted `offset`/`limit` reads instead of loading full documents and is the mechanism that lets the §7 read hierarchy actually work.

## When to Create a TOC

- Delegation: Use Haiku (Tier 1) to generate TOC tables from finished files.
- Any new `Reference/` or `Documentation/md/` file that is written above 200 lines, or any existing file that grows past 200 lines during edits.
- Immediately — not deferred to a cleanup pass.
- Created in the same session as the doc itself; do not close a session with an over-threshold doc that lacks a TOC.

## TOC File Naming and Location

- Same directory as the source file.
- Name: `[SourceFilename]_TOC.md` (e.g. `CPS_Integration_Spec_TOC.md`).
- Format: a two-column markdown table with header `| Line | Section |`, one row per `##` or `###` heading, line numbers absolute.

## After Adding or Removing a TOC

1. Update the corresponding row in the CLAUDE.md §7 doc table (Lines column + TOC column).
2. Update the TOC count line directly under the table ("TOC count: N docs").
3. Run `cps-refresh` so the new TOC is indexed and discoverable to query callers.

## Authoritative Registry

The CLAUDE.md §7 doc table is the single source of truth for TOC coverage. If a doc is over threshold and the TOC column is empty, the project is out of compliance and should be fixed before any new doc work begins. Do not rely on filesystem scans — the table is the canonical answer.

## Exemption — CLAUDE.md Files

CLAUDE.md is always fully loaded at session start, so a TOC produces no token savings for the file itself. CLAUDE.md files are exempt from the 200-line TOC threshold. Apply normal session-hygiene pressure instead: keep CLAUDE.md tight by folding stale phase history, retiring dead sections, and pushing rationale into Reference/*.md files.
"""

CAPTURE_TAXONOMY = """<!-- rev: 2 -->
# CPS Capture Taxonomy

CPS projects feed a second brain. Use the `cps-capture` skill to capture reusable knowledge.

**What to capture:** Reusable patterns (techniques applied 2+ times), design decisions (non-obvious choices with stated rationale), lessons (gotchas discovered the hard way), nascent ideas (low-friction, promote when ready), and roadmap items (committed intentions with horizon). Do not capture ephemeral task state (use `task` skill), code (commit it), or content already in CLAUDE.md or Reference/ docs (update those instead).

**Five buckets:**
- **Reference/Patterns/** — reusable techniques, design approaches, workflows
- **Reference/Decisions/** — ADR-style: decision + context + alternatives rejected + rationale
- **Reference/Lessons/** — gotchas, failure modes, "next time do X"
- **Reference/Ideas/** — nascent ideas, exploration candidates, "what if" items. Low bar — capture early, promote when ready
- **Reference/Roadmap/** — committed intentions not yet active tasks. Goal + rationale + horizon (Now/Next/Later)

Each bucket gets a `_INDEX.md` maintained by `cps-capture` on every capture.

**User-invoked capture.** Trigger phrases:
- Patterns: "save this pattern", "this is a good pattern", "capture this"
- Decisions: "record this decision", "worth remembering"
- Lessons: "lesson learned"
- Ideas: "add idea", "save idea", "capture idea"
- Roadmap: "add to roadmap", "add roadmap item"
- Any bucket: "add to second brain", "cps-capture"

**Promotion flow.**
- **Idea → Roadmap:** "promote [title] to roadmap" — creates a Roadmap entry referencing the source idea; updates idea Status to "Promoted".
- **Roadmap → Tasks:** "promote [title] to tasks" — spawns task entries in tasks.json via the `task` skill; updates roadmap Status to "Promoted".

**Claude-initiated capture (self-trigger).** Claude proactively flags a candidate mid-conversation when all four of these are true:
1. The knowledge is reusable across future sessions or projects
2. A future Claude would miss it if not captured
3. The *why* can be stated in one sentence
4. There is a clear bucket fit (Pattern / Decision / Lesson / Idea / Roadmap)

For Ideas, the self-trigger bar is lower: flag if something surfaces that seems worth exploring but isn't ready to be a task.

When Claude flags a candidate, it pauses, states it in one line, and asks "worth capturing?" before writing. Max one self-trigger prompt per ~5 exchanges to avoid interview mode.

**Capture flow:** User or Claude flags → Claude drafts content → Haiku (Tier 4) writes files + updates _INDEX.md → `cps-refresh` auto-runs → indexed.

**After capture:** If significant enough that future sessions must not miss it, suggest adding a pointer to this CLAUDE.md — but do not edit without explicit user approval.
"""

CORE_SECTION_BLOCK = """<!-- cps-core BEGIN rev: 4 -->
<!-- Managed by cps-init (cps_scaffold.py) — re-run cps-init to update. -->

## Delegation

Route Tier 1–4 mechanical work (file writes, mutations, formatting, transforms) to Haiku. Reserve Sonnet for architecture and decisions. Full heuristic: user preferences.

---

## Session Startup

Surface top 1–3 active tasks via §9 RECOMMEND. Load memory. Proceed to work.

---

## Document Access

Read in order until answered:

1. This CLAUDE.md
2. `_TOC.md` companion (for any `Reference/` or `Documentation/md/` doc over 200 lines)
3. Targeted `offset` / `limit` section read
4. Full doc

---

## Documentation

- `Reference/` — canonical design docs, patterns, decisions, lessons
- `Documentation/md/` — user-facing markdown docs

---

## Input / Output Folders

- `Input/` — Drop source materials here. CPS (Full profile) indexes `Input/**/*.md` via `source_paths`.
- `Output/` — Default drop zone for Claude-generated deliverables (reports, exports, presentations, one-off artifacts) outside `Documentation/` and `Reference/`. Write deliverables here unless directed elsewhere.

---

## 9. Task Module

Invoke the `task` skill. Session-start RECOMMEND surfaces the tiered backlog from `Reference/Claude/tasks.json`. Spec: `Reference/Claude/CPS_Task_Module.md`.

---

## 11. TOC Rule

Generate a `_TOC.md` companion for every `Reference/` or `Documentation/md/` file over 200 lines. Spec: `Reference/Claude/CPS_TOC_Rule.md`.

---

## 12. Capture Taxonomy

Route captures into five buckets under `Reference/`: Patterns, Decisions, Lessons, Ideas (low-friction — promote when ready), Roadmap (committed intentions, Now/Next/Later horizon). Promote: Idea → Roadmap → Tasks. Trigger phrases: "add idea", "add to roadmap", "promote [title] to roadmap", "promote [title] to tasks". Self-trigger gate: meet all four capture criteria (Ideas accept "what if" thoughts). Spec: `Reference/Claude/CPS_Capture_Taxonomy.md`.

<!-- cps-core END -->
"""

FULL_SECTION_BLOCK = """<!-- cps-full BEGIN rev: 2 -->
<!-- Managed by cps-init (cps_scaffold.py) — re-run cps-init to update. -->

## CPS Server Protocol

Run CPS semantic search on demand via `.cps/`.

- **Query** — Invoke `cps-query` (or `python .cps/cps_server.py search --query "..."`)
- **Refresh** — Invoke `cps-refresh` after doc or code changes
- **Capture** — Invoke `cps-capture` for knowledge entries

Availability condition: `.cps/cps_server.py` exists in the project root.

<!-- cps-full END -->
"""

# --------------------------------------------------------------------------
# Globals
# --------------------------------------------------------------------------

outcomes: List[Dict[str, str]] = []


def add_outcome(action: str, target: str) -> None:
    """Record an outcome (action + target)."""
    outcomes.append({"action": action, "target": target})


def ensure_directory(path: Path) -> bool:
    """
    Create directory if missing. Return True if created, False if already existed.
    """
    if path.exists():
        add_outcome("SKIPPED-dir", str(path))
        return False
    path.mkdir(parents=True, exist_ok=True)
    add_outcome("CREATED-dir", str(path))
    return True


def write_stub_file(
    file_path: Path, content: str, parent_was_just_created: bool
) -> None:
    """
    Write file if missing. If parent dir was just created, classify CREATED.
    If file existed but content differs, classify REPAIRED.
    If identical, SKIPPED. Record to outcomes.
    """
    if file_path.exists():
        existing = file_path.read_text(encoding="utf-8")
        if existing and existing.strip():
            add_outcome("SKIPPED", str(file_path))
            return
        file_path.write_text(content, encoding="utf-8")
        add_outcome("REPAIRED", str(file_path))
        return

    file_path.write_text(content, encoding="utf-8")
    if parent_was_just_created:
        add_outcome("CREATED", str(file_path))
    else:
        add_outcome("REPAIRED", str(file_path))


def get_embedded_rev(content: str) -> int:
    """Extract revision number from '<!-- rev: N -->' marker."""
    match = re.search(r"<!--\s*rev:\s*(\d+)\s*-->", content)
    if match:
        return int(match.group(1))
    return 0


def write_canonical_doc(
    file_path: Path, content: str, embedded_rev: int, force: bool = False
) -> None:
    """
    Write canonical doc with rev-aware logic:
    - missing → CREATED
    - existing rev < current_rev → UPGRADED (overwrite)
    - equal → SKIPPED
    - force=True → FORCED (always overwrite)
    """
    if file_path.exists():
        if force:
            file_path.write_text(content, encoding="utf-8")
            add_outcome("FORCED", str(file_path))
            return

        existing = file_path.read_text(encoding="utf-8")
        existing_rev = get_embedded_rev(existing)
        if existing_rev >= embedded_rev:
            add_outcome("SKIPPED", str(file_path))
            return

        file_path.write_text(content, encoding="utf-8")
        add_outcome(f"UPGRADED rev {existing_rev}->{embedded_rev}", str(file_path))
        return

    file_path.write_text(content, encoding="utf-8")
    add_outcome("CREATED", str(file_path))


def update_claude_md_block(
    file_path: Path,
    tag: str,
    block: str,
    embedded_rev: int,
    force: bool = False,
) -> None:
    """
    Replace text between '<!-- {tag} BEGIN rev: N -->' and '<!-- {tag} END -->' markers.
    If CLAUDE.md doesn't exist → create minimal CLAUDE.md with just this block → CREATED.
    If tag block missing → append → APPENDED.
    If existing rev < current_rev → replace → UPGRADED.
    If equal → SKIPPED.
    """
    if not file_path.exists():
        header = "# CLAUDE.md\n"
        file_path.write_text(header + "\n" + block + "\n", encoding="utf-8")
        add_outcome(f"CREATED w/ {tag}", str(file_path))
        return

    content = file_path.read_text(encoding="utf-8")
    if not content:
        content = ""

    begin_pattern = re.escape(f"<!-- {tag} BEGIN rev:")

    # Check if block exists
    match = re.search(begin_pattern + r"\s*(\d+)\s*-->", content)
    if match:
        existing_rev = int(match.group(1))
        if (not force) and (existing_rev >= embedded_rev):
            add_outcome(f"SKIPPED {tag} block", str(file_path))
            return

        # Replace the block
        escaped_tag = re.escape(tag)
        pattern = (
            f"(?s)<!--\\s*{escaped_tag}\\s*BEGIN\\s*rev:\\s*\\d+\\s*-->.*?"
            f"<!--\\s*{escaped_tag}\\s*END\\s*-->"
        )
        block_match = re.search(pattern, content)
        if block_match:
            new_content = (
                content[: block_match.start()]
                + block
                + content[block_match.end() :]
            )
            file_path.write_text(new_content, encoding="utf-8")
            add_outcome(
                f"UPGRADED {tag} rev {existing_rev}->{embedded_rev}",
                str(file_path),
            )
            return

    # Append at end
    needs_newline = not content.endswith("\n")
    appendage = ("\n\n" if needs_newline else "\n") + block + "\n"
    file_path.write_text(content + appendage, encoding="utf-8")
    add_outcome(f"APPENDED {tag} block", str(file_path))


def main() -> int:
    """Main scaffolding logic."""
    parser = argparse.ArgumentParser(
        description="CPS scaffold — creates CPS Core or Full folder structure"
    )
    parser.add_argument(
        "--path",
        default="",
        help="Target project directory (default: current working directory)",
    )
    parser.add_argument(
        "--profile",
        choices=["core", "full"],
        default="",
        help="Profile: core or full (default: prompt interactively)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing canonical docs regardless of rev marker",
    )

    args = parser.parse_args()

    # Determine target path
    if args.path:
        target_path = Path(args.path)
    else:
        target_path = Path.cwd()

    # Determine profile
    profile_name = args.profile
    if not profile_name:
        print()
        print("CPS Scaffold")
        print("============")
        print(f"Target: {target_path}")
        print()
        print("Select profile:")
        print("  1) Core   - scaffold + three pillars, no Python runtime")
        print("  2) Full   - Core + CPS Server Protocol section in CLAUDE.md")
        print()
        choice = input("Choose [1-2]: ").strip()
        if choice == "1":
            profile_name = "core"
        elif choice == "2":
            profile_name = "full"
        else:
            print("Invalid choice. Aborting.")
            return 1

    print()
    print(f"Scaffolding CPS ({profile_name}) into: {target_path}")
    print()

    # Ensure target exists
    target_path.mkdir(parents=True, exist_ok=True)
    target_path = target_path.resolve()

    # --------------------------------------------------------------------------
    # Step 1: directories
    # --------------------------------------------------------------------------

    dir_specs = [
        "Reference",
        "Reference/Claude",
        "Reference/Patterns",
        "Reference/Decisions",
        "Reference/Lessons",
        "Reference/Ideas",
        "Reference/Roadmap",
        "Documentation",
        "Documentation/md",
        "Input",
        "Output",
    ]

    dir_created: Dict[str, bool] = {}
    for rel in dir_specs:
        full = target_path / rel
        dir_created[rel] = ensure_directory(full)

    # --------------------------------------------------------------------------
    # Step 2: _INDEX.md stubs
    # --------------------------------------------------------------------------

    write_stub_file(
        target_path / "Reference/Patterns/_INDEX.md",
        INDEX_PATTERNS,
        dir_created["Reference/Patterns"],
    )
    write_stub_file(
        target_path / "Reference/Decisions/_INDEX.md",
        INDEX_DECISIONS,
        dir_created["Reference/Decisions"],
    )
    write_stub_file(
        target_path / "Reference/Lessons/_INDEX.md",
        INDEX_LESSONS,
        dir_created["Reference/Lessons"],
    )
    write_stub_file(
        target_path / "Reference/Ideas/_INDEX.md",
        INDEX_IDEAS,
        dir_created["Reference/Ideas"],
    )
    write_stub_file(
        target_path / "Reference/Roadmap/_INDEX.md",
        INDEX_ROADMAP,
        dir_created["Reference/Roadmap"],
    )

    # --------------------------------------------------------------------------
    # Step 3: canonical reference docs (rev-aware)
    # --------------------------------------------------------------------------

    write_canonical_doc(
        target_path / "Reference/Claude/CPS_Task_Module.md",
        TASK_MODULE,
        TASK_MODULE_REV,
        args.force,
    )
    write_canonical_doc(
        target_path / "Reference/Claude/CPS_TOC_Rule.md",
        TOC_RULE,
        TOC_RULE_REV,
        args.force,
    )
    write_canonical_doc(
        target_path / "Reference/Claude/CPS_Capture_Taxonomy.md",
        CAPTURE_TAXONOMY,
        CAPTURE_REV,
        args.force,
    )

    # --------------------------------------------------------------------------
    # Step 4: CLAUDE.md sections
    # --------------------------------------------------------------------------

    claude_md = target_path / "CLAUDE.md"
    update_claude_md_block(claude_md, "cps-core", CORE_SECTION_BLOCK, CORE_SECTION_REV, args.force)

    if profile_name == "full":
        update_claude_md_block(claude_md, "cps-full", FULL_SECTION_BLOCK, FULL_SECTION_REV, args.force)

    # --------------------------------------------------------------------------
    # Report
    # --------------------------------------------------------------------------

    print()
    print("Outcomes")
    print("--------")

    # Sort outcomes by action, then target
    sorted_outcomes = sorted(outcomes, key=lambda x: (x["action"], x["target"]))

    # Print table header
    print(f"{'Action':<40} {'Target':<60}")
    print(f"{'-' * 40} {'-' * 60}")

    for outcome in sorted_outcomes:
        action = outcome["action"]
        target = outcome["target"]
        print(f"{action:<40} {target:<60}")

    # Count outcomes
    created_count = sum(
        1 for o in outcomes if o["action"].startswith("CREATED")
    )
    repaired_count = sum(
        1 for o in outcomes if o["action"].startswith("REPAIRED")
    )
    upgraded_count = sum(
        1
        for o in outcomes
        if o["action"].startswith("UPGRADED")
        or o["action"].startswith("APPENDED")
        or o["action"].startswith("FORCED")
    )
    skipped_count = sum(1 for o in outcomes if o["action"].startswith("SKIPPED"))

    print()
    print(
        f"Summary: {created_count} created, {repaired_count} repaired, "
        f"{upgraded_count} upgraded/appended, {skipped_count} skipped."
    )
    print()
    print(f"Done. Profile: {profile_name}")

    if profile_name == "full":
        print()
        print(
            "Next step: run cps-setup (full) to deploy the Python runtime and .cps/ database."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
