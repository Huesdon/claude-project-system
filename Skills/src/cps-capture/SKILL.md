---
name: cps-capture
description: >
  Shared skill — captures reusable knowledge into the project's CPS Reference buckets
  (Patterns / Decisions / Lessons / Ideas / Roadmap) per CLAUDE.md §12 taxonomy. Classifies
  the capture, drafts structured content, delegates the file write and _INDEX.md update to
  Haiku, auto-runs a targeted ingest via subprocess CLI (no MCP required) so the capture is
  immediately queryable, and reports the result in one line. Supports both user-invoked
  capture and Claude-initiated self-trigger under the four-condition gate. Also handles
  promotion: Idea→Roadmap and Roadmap→Tasks.
  Triggers on: "save this pattern", "capture this", "lesson learned", "worth remembering",
  "record this decision", "add to second brain", "this is a good pattern", "cps-capture",
  "add idea", "save idea", "capture idea", "add to roadmap", "add roadmap item",
  "promote to roadmap", "promote to tasks".
---

# cps-capture — Second-Brain Knowledge Capture

## Purpose

Turn reusable knowledge discovered during a session into a persistent, indexed artifact in the
project's CPS Reference tree. Five buckets — Patterns, Decisions, Lessons, Ideas, Roadmap —
each backed by an `_INDEX.md`. Captured files are immediately re-indexed via subprocess so the
next `cps_search` can surface them. Also handles promotion flows: Idea→Roadmap and
Roadmap→Tasks.

## Prerequisites

- CPS scaffold must exist for the target bucket directory (e.g. `Reference/Ideas/`).
- `.cps/cps_server.py` must exist for the auto-ingest step (Step 5).
- If scaffold is missing: "CPS scaffold isn't set up for that bucket. Run the `cps-init` skill first."

## Finding the Project Root

Use Glob to find `.cps/cps_server.py` in the workspace. The parent of `.cps/` is the project
root. Used in Step 5 for the targeted ingest.

---

## Mode A — Capture (new entry)

### Step 1 — Classify the bucket

Choose the bucket silently if obvious from the user's phrasing; ask once if ambiguous.

- **Pattern** — reusable technique, workflow, or design approach applied (or to be applied) 2+
  times. Answers "how do I do X well".
  Triggers: "save this pattern", "this is a good pattern", "capture this" (when pattern-shaped).
- **Decision** — ADR-style: non-obvious choice + context + alternatives rejected + rationale.
  Answers "why did we pick X over Y".
  Triggers: "record this decision", "worth remembering" (when decision-shaped).
- **Lesson** — gotcha, failure mode, or "next time do X" note. Answers "what went wrong and
  how do I avoid it".
  Triggers: "lesson learned".
- **Idea** — nascent idea, exploration candidate, "what if" item. Low bar — capture early,
  promote when ready.
  Triggers: "add idea", "save idea", "capture idea".
- **Roadmap** — committed intention, not yet an active task. Has goal, rationale, and horizon
  (Now/Next/Later).
  Triggers: "add to roadmap", "add roadmap item".

**Reject the capture** (tell the user, do not write a file) if any of the following are true:
- Ephemeral task state → redirect to the `task` skill
- Raw source code → commit it; do not capture
- Already in CLAUDE.md or an existing `Reference/*.md` → update that file, name it
- Fails the four-condition gate (self-triggered captures only; user-invoked captures proceed)

### Step 2 — Draft structured content

Draft the file body using the template for the chosen bucket. Use the user's own words; do not
embellish.

**Pattern template:**
```
# [Title]

**Captured:** YYYY-MM-DD
**Applies to:** [scope — project, language, tool, domain]

## Context
One paragraph on when this pattern shows up.

## Technique
Step-by-step or prose description of the approach.

## When to use
- [trigger condition]

## When NOT to use
- [anti-pattern or disqualifier]

## Examples
At least one concrete example, preferably two.
```

**Decision template:**
```
# [Title]

**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by [link] | Deprecated

## Context
What forced the decision. Constraints, deadlines, stakeholders.

## Decision
The choice made, in one sentence.

## Alternatives rejected
- **Option A** — why it was rejected
- **Option B** — why it was rejected

## Rationale
Why the chosen option wins. Include any tradeoffs explicitly accepted.

## Consequences
Downstream effects — what becomes easier, harder, or newly required.
```

**Lesson template:**
```
# [Title]

**Captured:** YYYY-MM-DD
**Severity:** Low | Medium | High

## Symptom
What was observed. The surface-level problem.

## Root cause
What was actually wrong underneath.

## Fix
What resolved it.

## Prevention
What to do next time to avoid hitting this again.
```

**Idea template:**
```
# [Title]

**Captured:** YYYY-MM-DD
**Status:** Active | Promoted | Parked | Rejected
**Area:** [domain/module/feature area]

## What
One paragraph: what the idea is.

## Why it's interesting
Why this is worth exploring — the problem it solves or opportunity it opens.

## Open questions
- [question]

## Notes
Any links, references, or rough thoughts.
```

**Roadmap template:**
```
# [Title]

**Date:** YYYY-MM-DD
**Status:** Active | Complete | Deferred | Cancelled | Promoted
**Horizon:** Now | Next | Later
**Source idea:** [filename or N/A]

## Goal
What this achieves in one sentence.

## Rationale
Why this is on the roadmap — the value or problem it addresses.

## Scope
What's in and what's explicitly out.

## Dependencies
- [dependency or N/A]

## Success criteria
- [measurable outcome]
```

### Step 3 — Build the filename

Slug the title as kebab-case, prefix with today's date:

```
YYYY-MM-DD-short-title.md
```

Target path by bucket:
- Pattern → `Reference/Patterns/YYYY-MM-DD-short-title.md`
- Decision → `Reference/Decisions/YYYY-MM-DD-short-title.md`
- Lesson → `Reference/Lessons/YYYY-MM-DD-short-title.md`
- Idea → `Reference/Ideas/YYYY-MM-DD-short-title.md`
- Roadmap → `Reference/Roadmap/YYYY-MM-DD-short-title.md`

### Step 4 — Delegate the write to Haiku (Tier 4)

Pass Haiku the minimal payload only — no conversation history, no CLAUDE.md, no unrelated context:

- `target_path` — absolute path from Step 3
- `file_body` — drafted content from Step 2
- `index_path` — absolute path to the bucket's `_INDEX.md`
- `index_line` — `- [Title](filename.md) — one-line hook`

Haiku's job (no judgment, no rewriting):
1. Write `file_body` to `target_path`
2. Append `index_line` to `index_path` (add trailing newline if missing)
3. Return `{written: <path>, index_updated: true|false, error: null|<message>}`

### Step 5 — Auto-run targeted ingest via subprocess

From the project root using the Bash tool:

```bash
python .cps/cps_server.py ingest --files=<target_path>,<index_path>
```

Parse the JSON result. If `files_processed >= 1`, the capture is live and indexed.

On non-zero exit: the file is still written — tell the user to run `cps-refresh` manually.
Do not roll back the write.

### Step 6 — Report

Single-line format:
```
Captured [Pattern|Decision|Lesson|Idea|Roadmap] → Reference/<bucket>/<filename>. Indexed. <chunks_created> chunks added.
```

If the capture is load-bearing enough that future sessions must not miss it, optionally add:
```
Suggest adding a pointer in CLAUDE.md §<section>? (requires explicit approval)
```

Never edit CLAUDE.md from this skill. A pointer edit is always a separate, user-approved action.

---

## Mode B — Promote (Idea → Roadmap)

Triggered by: "promote [title] to roadmap", "promote idea [title]".

### Step 1 — Locate the source idea file

Glob `Reference/Ideas/*.md` and find the file matching the title (exact or fuzzy). Read it.
If not found, ask the user to confirm the title.

### Step 2 — Draft the Roadmap entry

Use the Roadmap template (Mode A → Step 2). Pre-fill:
- `**Source idea:**` → source idea filename
- `**Status:**` → Active
- Pull Goal from idea's "What" section; pull Rationale from "Why it's interesting"
- Leave Horizon, Scope, Dependencies, Success criteria for user to fill in (or ask)

### Step 3 — Update the source idea file

Change `**Status:** Active` → `**Status:** Promoted` in the idea file.

### Step 4 — Delegate both writes to Haiku (Tier 4)

Pass Haiku:
- New roadmap file: `target_path` + `file_body` + roadmap `index_path` + `index_line`
- Idea update: `idea_path` + `old_status_line` (`**Status:** Active`) + `new_status_line`
  (`**Status:** Promoted`)

Haiku's job:
1. Write roadmap file
2. Append roadmap index line
3. Apply status replace in idea file (find-and-replace, not full rewrite)
4. Return `{roadmap_written, idea_updated, index_updated, error}`

### Step 5 — Auto-ingest both files

```bash
python .cps/cps_server.py ingest --files=<roadmap_path>,<idea_path>,<roadmap_index_path>
```

### Step 6 — Report

```
Promoted Idea → Roadmap: Reference/Roadmap/<filename>. Idea marked Promoted. Indexed.
```

---

## Mode C — Promote (Roadmap → Tasks)

Triggered by: "promote [title] to tasks", "add [roadmap title] to backlog".

Defer to the `task` skill for this operation. That skill owns `tasks.json` and the task creation
flow. Hand off by saying:

> "To promote this roadmap item to the task backlog, invoke the `task` skill with:
> 'add task: [title] — [one-line goal from roadmap]'"

Then update the roadmap item's Status to "Promoted" via Haiku (same find-and-replace as Mode B
Step 4 idea update), and re-ingest the roadmap file.

---

## Self-Trigger Rules (Claude-initiated capture)

Claude may proactively flag a capture candidate mid-conversation only when **all four** are true:

1. The knowledge is reusable across future sessions or projects
2. A future Claude would miss it (not already in CLAUDE.md or a Reference doc)
3. The *why* can be stated in one sentence
4. There is a clear bucket fit — Pattern, Decision, Lesson, Idea, or Roadmap

**Ideas have a lower bar:** flag if something surfaces that seems worth exploring but isn't ready
to be a task — a "what if" thought with enough specificity to be worth tracking. Only the
first and third conditions need to hold for an Idea self-trigger.

When all conditions hold: pause, state the candidate in one line, ask "Worth capturing?" Wait for
explicit user approval before running Steps 1–6. If the user declines or ignores, drop silently.

**Governor:** Maximum one self-trigger prompt per ~5 exchanges. Do not turn the session into an
interview.

## User-Invoked Capture

All trigger phrases route to Mode A (Capture) unless "promote" is in the phrase (→ Mode B or C).

**Capture triggers (Mode A):**
"save this pattern", "this is a good pattern", "capture this", "lesson learned", "worth
remembering", "record this decision", "add idea", "save idea", "capture idea",
"add to roadmap", "add roadmap item", "add to second brain", "cps-capture".

**Promotion triggers:**
- Mode B: "promote [title] to roadmap", "promote idea [title]"
- Mode C: "promote [title] to tasks", "add [title] to backlog"

The four-condition gate does NOT apply to user-invoked captures — if the user asks to capture it,
capture it. Only the hard rejections in Mode A Step 1 (ephemeral state, raw code,
already-documented) still apply.

## Error Handling

- **Scaffold missing:** halt, direct to `cps-init`. Do not create directories from this skill.
- **`_INDEX.md` missing in a valid bucket:** halt and report which bucket. Scaffold repair is
  `cps-init`'s job.
- **Haiku write fails:** report the error and target path. Skip Step 5. Do not retry automatically.
- **Subprocess ingest fails:** file is still written. Tell user to run `cps-refresh` manually.
  Do not roll back the write.
- **Filename collision (same slug same day):** append `-2`, `-3`. Do not overwrite.
- **Source idea not found (Mode B):** halt, ask user to confirm the title.
- **Clearly ephemeral capture request:** decline in one sentence, point to correct destination.

## Interaction with Other Skills

- `cps-init` owns scaffold creation. This skill never creates bucket directories or `_INDEX.md`.
- `cps-query` reads what this skill writes. Captures become searchable within seconds of Step 5.
- `cps-refresh` is the fallback if Step 5 errors.
- `task` owns `tasks.json` and Roadmap→Tasks promotion (Mode C hands off to it).