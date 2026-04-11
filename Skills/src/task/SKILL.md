---
name: task
description: >
  Universal project task backlog manager for any Claude Cowork project. Maintains a
  single source of truth at Reference/Claude/tasks.json containing every tier (T1,
  T2, T3, Roadmap) in one file — no separate backlog. On first run, creates the file
  and writes the standard Task Module section into the project CLAUDE.md. After
  init, manages the backlog: add tasks, mark complete with log, reprioritize,
  review, health, and get session recommendations. When T1/T2 is empty, surfaces
  Roadmap items to promote, or Ideas to promote to Roadmap. Every prompt uses
  AskUserQuestion; task pickers use numbered buttons (1/2/3) so long titles never
  break rendering. Invoke when the user says: "add a task", "log this as a task",
  "what should I work on", "reprioritize the backlog", "mark that done", "task
  backlog", "show me open tasks", "task status", "run task", or opens a new
  project and wants structured task tracking. Works standalone in any Cowork
  project.
---

# task — Project Task Backlog Manager

Single canonical file: `Reference/Claude/tasks.json` holds every task at every tier (T1, T2, T3, Roadmap). There is no separate backlog file. Order within the file is authoritative: REPRIORITIZE is the only way tasks move within the stack.

Completion log: `Reference/Claude/tasks_completed.log` (one line per completed task, lazy-created on first COMPLETE).

Completed tasks are removed from `tasks.json` and appended to the log.

---

## Response Button Rule (MANDATORY)

**Every question without exception uses `AskUserQuestion`.** No question is ever asked in prose. A response that ends with a question in plain text is a violation of this rule.

### Task-picker flows — Numbered button pattern

When the user is picking from a list of tasks, roadmap items, or ideas (anything with long titles), use the **numbered pattern**:

1. Present the list as a short numbered prose block above the buttons:
   ```
   1. Grep for stale 'double-click the cmd' references — T3
   2. Remove residual Windows-only language from cps-init SKILL.md — T3
   3. Update cps-setup SKILL.md Step 6 wording — T3
   ```
2. Present `AskUserQuestion` with button **labels** as single characters: `1`, `2`, `3`, plus a fourth option like `Show all`. The long title goes in the option **description** field, not the label.

This keeps buttons short and guarantees rendering even when titles are long.

**Binary and worded-option flows stay worded.** Short-option flows (tier picker: `T1` / `T2` / `T3` / `Roadmap`, Patch gate Yes/Not-yet, Impact scan multi-select) use their natural labels — the numbered pattern is only for picking from a list of items with long names.

---

## JSON Schema

```json
{
  "meta": {
    "last_updated": "YYYY-MM-DD",
    "last_updated_note": "optional human note",
    "completions_since_reprioritization": 0,
    "reprioritize_threshold": 5,
    "last_reprioritized": "YYYY-MM-DD",
    "reprioritization_strategy": "dependency-first"
  },
  "tasks": [
    {
      "id": "t2-short-slug",
      "title": "Task Title",
      "tier": "T1 | T2 | T3 | Roadmap",
      "status": "pending | in_progress | blocked",
      "description": "One sentence, 80-120 chars max.",
      "depends_on": ["Title of dependency task"],
      "unblocks": ["Title of task this unblocks"],
      "requires_patch": true
    }
  ]
}
```

**Tier conventions:** T1 = architectural/high design impact, T2 = subsystem, T3 = docs/polish, Roadmap = future.
**Status values:** `pending`, `in_progress`, `blocked`.
**Single-file rule:** Every tier lives in `tasks.json`. Order is maintained by REPRIORITIZE (T1 before T2 before T3 before Roadmap, dependencies before dependents within each tier). There is no `tasks_backlog.json`.
**Description rule:** One sentence, 80-120 chars. No implementation details, no doc references. WHAT not HOW.
**`requires_patch`:** Optional. Set `true` if the task modifies scaffold templates that downstream projects depend on — triggers a patch-catalog gate on COMPLETE.
**`completions_since_reprioritization`:** Still incremented on every COMPLETE for HEALTH visibility, but COMPLETE no longer auto-prompts when it crosses the threshold. Invoke REPRIORITIZE manually when you want it.

---

## Token Discipline

**Hard cap: 15 tasks max loaded per operation.** If `tasks.json` exceeds 15 tasks, RECOMMEND reads only the first 15 (they are already priority-sorted). REPRIORITIZE, REVIEW, and HEALTH read the full file unconditionally.

- Read the file once per operation, parse only the fields needed.
- For ADD / COMPLETE / RECOMMEND: read the file, make the change in memory, write back in one shot.
- Never re-read a file already loaded in the current turn.

---

## Step 1: Check Init State

Glob for `Reference/Claude/tasks.json`. If missing → run Init. If present → skip to the requested sub-flow.

---

## Init Flow (first run only)

Create `Reference/Claude/tasks.json` with empty structure:

```json
{
  "meta": {
    "last_updated": "[today]",
    "last_updated_note": "initialized",
    "completions_since_reprioritization": 0,
    "reprioritize_threshold": 5,
    "last_reprioritized": "[today]",
    "reprioritization_strategy": "dependency-first"
  },
  "tasks": []
}
```

Do NOT create `tasks_completed.log` at init — it is created lazily on the first COMPLETE call.

### CLAUDE.md Task Module Section (overwrite policy)

Open the project CLAUDE.md (create a minimal one if none exists). Search for any existing section heading matching:
- `## Task Backlog` (any subtitle)
- `## Task Module` (any subtitle)
- Any numbered variant (`## 9. Task Backlog`, `## 9. Task Module`, etc.)

**If found:** Find-and-replace the entire section (heading through end of section, up to but not including the next `##` heading) with the standard Task Module text below.

**If not found:** Append the standard Task Module text to the end of CLAUDE.md.

Preserve any project-specific section number prefix if the existing section had one (e.g. `## 9. ...` stays `## 9. Task Module — Backlog Management Standard`).

**Standard Task Module text to write:**

```markdown
## Task Module — Backlog Management Standard

> **Applies to:** Any project that uses the `task` skill for cross-session backlog management. This section is the standard scaffold installed by the `task` skill on first run. Do not edit individual rules without updating the skill.

### Single Source of Truth

`Reference/Claude/tasks.json` holds every task at every tier (T1, T2, T3, Roadmap). There is no separate backlog file. Order within the file is authoritative — REPRIORITIZE is the only way tasks move within the stack.

### Session Start — RECOMMEND Flow

At session start, read `Reference/Claude/tasks.json` and surface the top 1–3 actionable T1/T2 tasks via `AskUserQuestion` before any other work begins. Trust the existing order: REPRIORITIZE produces a dependency-aware ranking, so the top of the file is already the right answer. Wait for user confirmation before starting.

**Button rendering rule:** Task-picker flows use a numbered prose list plus number-only button labels (`1` / `2` / `3` / `Show all`) so long titles never break rendering. The full title appears in the option description, not the button label.

**Before surfacing tasks:** Check for in-progress tasks from last session (Step 2a) and for invalid `"completed"` status values (Step 2b). Resolve both before picking new work.

**Empty state:** If there are no actionable T1/T2 tasks (all complete, all blocked, or none of that tier exist), run the EMPTY-STATE FLOW to surface Roadmap items to promote to tasks, or Ideas to promote to the Roadmap.

**Cross-session signal:** When the user selects a task, immediately write `status: "in_progress"` for that task before starting work. This is what Step 2a detects next session.

### Immediate Completion (MANDATORY)

When a task is fully done — all steps finished, files written, docs propagated — call `task COMPLETE` immediately. Do **not** wait for session close or explicit user instruction. COMPLETE is authoritative: the task is removed from `tasks.json` and a line is appended to `tasks_completed.log`. If you mark the wrong task by mistake, recover via `task ADD`; the log preserves history. Never leave a finished task in `pending` or `in_progress` between work items — `tasks.json` must stay in sync with reality at all times.

### Patch Gate (if `requires_patch: true`)

Tasks that modify scaffold templates downstream projects depend on must be flagged with `"requires_patch": true`. On COMPLETE, prompt: *"This task touched scaffold templates — did you update the patch catalog and rebundle?"* with options **"Yes, done"** / **"Not yet — reopen the task"**. If not yet, the task is restored to `in_progress`, the completion log line is removed, and the counter is decremented.

### Reprioritization

REPRIORITIZE is invoked manually when the user wants it. The meta counter `completions_since_reprioritization` is still incremented on every COMPLETE so HEALTH can surface it, but COMPLETE no longer auto-prompts to run REPRIORITIZE. Run it on demand: *"reprioritize"* / *"reorder the backlog"*.

### Keep tasks.json Current

`Reference/Claude/tasks.json` is the cross-session task backlog and the single source of truth. When new work is discovered mid-session — either by Claude noticing a follow-up or by the user mentioning something — call `task ADD` immediately rather than mentioning it in chat and forgetting. Treat user-added entries as authoritative: do not second-guess priority, retitle, or reorder them without explicit instruction.

### Propagate Design Changes to Documentation Same-Session

After any design decision or architectural change, update all relevant `Reference/*.md` and `Documentation/md/*.md` files in the same session. Create a new Reference doc if none exists for the topic. Do not close a session with design decisions captured only in `tasks.json` or session memory — they must be fully encoded in documentation files.

If the project uses CPS (Claude Project System), CPS indexes these docs; stale docs mean stale query results. **After doc updates, run `cps-refresh` to re-index changed files before session close.**
```

Confirm: "Task backlog initialized. Standard Task Module section written to CLAUDE.md. Ready to add your first task."

---

## RECOMMEND (session startup)

**Token budget: minimal.** This runs on every session open.

1. Read `Reference/Claude/tasks.json` only. Parse tasks array. If more than 15 tasks, truncate to first 15 (they are priority-sorted).

### Step 2a — In-progress check (runs before surfacing any pending work)

If any task has `"status": "in_progress"`, pause and ask first via `AskUserQuestion`:

- **"Yes, mark complete"** — run COMPLETE for that task (remove + log), then continue to step 3.
- **"No, keep working on it"** — surface it as the sole recommendation (skip steps 3–6), then go to step 7.

Label the question: *"'[Title]' was in progress last session — was it completed?"*

### Step 2b — Invalid status guard

If any task has `"status": "completed"` (not a valid active-file status — tasks must be removed on completion, not status-flagged), treat it as a data error and ask via `AskUserQuestion`:

- **"Remove and log it"** — run COMPLETE (removes from array, appends to log).
- **"Reopen as pending"** — set `status: "pending"` and write back.

Label the question: *"'[Title]' has status 'completed' but was never removed from tasks.json — fix it now?"*

### Step 3 — Filter and pick

3. Filter remaining: skip `blocked` tasks, skip T3 and Roadmap tiers (RECOMMEND only surfaces T1/T2).
4. From remaining, select top 1-3 by position order (first = highest priority).
5. For each candidate, extract only: `title`, `tier`, `status`.

### Step 4 — Present (numbered button pattern)

6. Print the numbered list in prose, one line per candidate:
   ```
   1. [Title] — [tier]
   2. [Title] — [tier]
   3. [Title] — [tier]
   ```

   Then present `AskUserQuestion` with up to 4 options:
   - Label `1` / description: full title
   - Label `2` / description: full title
   - Label `3` / description: full title
   - Label `Show all` / description: "See every task in tasks.json including T3 and Roadmap"

   Only include numbers that correspond to real candidates. If there are 2 tasks, only options `1`, `2`, and `Show all`.

### Step 5 — Mark in progress

7. When the user selects a numbered task → immediately write `status: "in_progress"` for that task to `tasks.json` before starting any work. This creates the cross-session signal Step 2a detects next session.

   If the user selects **"Show all"** → run REVIEW flow instead.

### Empty state

If step 4 yields 0 candidates (all blocked, or no T1/T2 tasks in the file at all) → run **EMPTY-STATE FLOW** instead of presenting an empty list.

**Do NOT:** read full descriptions, load dependency chains, or enumerate T3/Roadmap during RECOMMEND. The goal is a fast, cheap pick-list.

---

## EMPTY-STATE FLOW

Triggered when the T1/T2 backlog has no actionable tasks (empty, all blocked, or only T3/Roadmap entries exist). Surfaces the next logical work from the Roadmap → Ideas chain.

### Step 1 — Check Roadmap

Glob `Reference/Roadmap/*.md`. Exclude `_INDEX.md`.

**If roadmap files exist:**

1. Read `Reference/Roadmap/_INDEX.md` for the title list (format: `- [Title](filename.md) — hook`).
2. Extract up to 3 titles (first 3 lines).
3. Print numbered list in prose:
   ```
   1. [Title 1] — [hook]
   2. [Title 2] — [hook]
   3. [Title 3] — [hook]
   ```
4. Present `AskUserQuestion` with options labeled `1` / `2` / `3` / `Skip for now` (descriptions contain the full title and hook).

   Label the question: *"T1/T2 backlog is empty. Your roadmap has N items — promote one to start work?"*

5. If user picks `1` / `2` / `3` → run **PROMOTE FROM ROADMAP** with the corresponding title.
6. If user picks `Skip for now` → end. Do not automatically surface Ideas.

**If no roadmap files → proceed to Step 2.**

### Step 2 — Check Ideas

Glob `Reference/Ideas/*.md`. Exclude `_INDEX.md`.

**If idea files exist:**

1. Read `Reference/Ideas/_INDEX.md` for the title list.
2. Extract up to 3 titles.
3. Print numbered list in prose.
4. Present `AskUserQuestion` with options labeled `1` / `2` / `3` / `Skip for now`.

   Label the question: *"Roadmap is empty too. You have N ideas — promote one to the roadmap to get started?"*

5. If user picks a number → tell the user:

   > *"To promote '[title]' to the Roadmap, invoke the `cps-capture` skill and say 'promote [title] to roadmap'. Once it is on the roadmap, come back here and I will convert it to a task."*

6. If user picks `Skip for now` → end.

**If no idea files either:**

Say: *"Backlog, roadmap, and ideas are all empty. Use `task ADD` to add a task directly, or `cps-capture` to save an idea or roadmap item."*

---

## PROMOTE FROM ROADMAP

Triggered when the user selects a roadmap item to convert into an active T1/T2 task.

### Step 1 — Locate the roadmap file

Glob `Reference/Roadmap/*.md` (exclude `_INDEX.md`). Find the file whose name or content matches the selected title (fuzzy match on filename slug). Read it.

If not found: ask the user via `AskUserQuestion` to confirm the exact filename from a numbered list of candidates.

### Step 2 — Extract task fields

From the roadmap file, read:
- **Title** — the `# Title` heading at the top of the file.
- **Goal** — content of the `## Goal` section (one sentence). This becomes the default task description.
- **Horizon** — `Now | Next | Later` from the frontmatter. Use as a tier hint: `Now` → T1, `Next` → T2, `Later` → T2.

### Step 3 — Confirm task fields

Present a single `AskUserQuestion` (this is a worded-options flow, not a numbered-picker flow):

Options:
- **"T1 — Architectural"** — promote as T1 with Goal as description
- **"T2 — Subsystem"** — promote as T2 with Goal as description
- **"Edit before adding"** — user will provide custom title and description in a follow-up turn

Label the question: *"Promoting '[title]' from Roadmap. Confirm tier?"* (Print the Goal sentence in prose above the buttons so the user can see what will become the description.)

If `Edit before adding`: ask for title and description in a follow-up plain-text exchange (NOT an `AskUserQuestion` — free-text input is required).

### Step 4 — Add the task

Run the ADD flow with the confirmed fields:
- `title` = roadmap file title
- `tier` = T1 or T2 (from Step 3)
- `description` = Goal sentence (trimmed to 80-120 chars; truncate if needed, never pad)
- `depends_on` = [] (roadmap dependencies are narrative, not task-graph; do not carry over)
- `status` = `pending`

Write to `tasks.json` via the standard ADD logic.

### Step 5 — Update the roadmap file status

Edit the roadmap file: find the line `**Status:** Active` and replace with `**Status:** Promoted`.

If the project has CPS (`.cps/cps_server.py` exists), run a targeted ingest:
```bash
python .cps/cps_server.py ingest --files=<roadmap_file_path>
```

### Step 6 — Report and offer immediate start

Single line report:
```
Promoted '[title]' from Roadmap → added as [tier] task in tasks.json. Roadmap entry marked Promoted.
```

Then present via `AskUserQuestion`:
- **"Yes, set to in_progress"** — update the task status in tasks.json to `in_progress`.
- **"Leave as pending"** — no change.

Label: *"Start working on it now?"*

---

## ADD

Extract what you can from context. Only ask for missing required fields — use `AskUserQuestion` for each gap.

| Field | Required | Notes |
|-------|----------|-------|
| title | Yes | Verb + noun ("Build login page") |
| tier | Yes | T1 / T2 / T3 / Roadmap |
| description | Yes | One sentence, 80-120 chars. |
| depends_on | No | Array of task titles |
| unblocks | No | Array of task titles |
| requires_patch | No | Set `true` if task touches scaffold templates (triggers patch gate on COMPLETE) |

If `tier` is missing, present `AskUserQuestion` with options: **"T1 — Architectural"** / **"T2 — Subsystem"** / **"T3 — Docs/Polish"** / **"Roadmap — Future"**. (Short worded labels — no numbered pattern needed.)

Generate `id` as `[tier-lowercase]-[slug]` (e.g. `t2-help-system`).
Set `status` to `pending` unless context indicates otherwise.

Read `tasks.json` → parse → append new task object → write back.
Update `meta.last_updated` and `meta.last_updated_note`.

**Insertion position:** New tasks are appended to the end of the `tasks` array. REPRIORITIZE is responsible for placing them in the correct position within the tier stack.

---

## COMPLETE

Optimistic + batched. Happy-path worst case is **1 prompt** (the batched follow-up call). Best case is **0 prompts**. With `requires_patch`, add 1 blocking gate on top.

### Step 1 — Remove and log (MANDATORY)

Read `tasks.json` → find task by title (case-insensitive substring match) → capture `id`, `title`, `tier`, `requires_patch`, `depends_on` → remove from the array → write back.

Update `meta.last_updated` (today) and `meta.last_updated_note` (`"completed: [Title]"`).

Append one line to `Reference/Claude/tasks_completed.log`:

```
YYYY-MM-DD | task-id | Task Title
```

Lazy-create the log file if missing — no header.

### Step 2 — Counter increment (MANDATORY)

Increment `meta.completions_since_reprioritization` by 1. This is kept for HEALTH visibility only; COMPLETE does **not** auto-prompt to run REPRIORITIZE when it crosses the threshold. The user invokes REPRIORITIZE manually.

### Step 3 — Patch gate (blocking, only if `requires_patch: true`)

If the completed task had `"requires_patch": true`, present `AskUserQuestion`:

- **"Yes, done"** — proceed to Step 4.
- **"Not yet — reopen the task"** — restore task to `in_progress` in `tasks.json`, remove the completion log line just appended, decrement `meta.completions_since_reprioritization` by 1, and stop.

Label: *"This task touched scaffold templates — did you update the patch catalog and rebundle?"*

If `requires_patch` is absent or false, skip this step entirely.

### Step 4 — Batched Impact scan (single `AskUserQuestion` call, only if dependents exist)

Scan the remaining tasks in `tasks.json` for any that list the completed title in their `depends_on`. If one or more exist, present a single `AskUserQuestion` call with one question (`multiSelect: true`):

- Header: `Unblocked`
- Question: *"Completing this unblocks N tasks — which should move to in_progress?"*
- Options: one per unblocked dependent. Label = single-digit index (`1`, `2`, `3`, …); description = full title. If there are 4 or more dependents, show the top 3 by `tasks.json` order plus **"None"**; the remaining dependents stay `pending` (user can move them manually later).

After the call: for each dependent the user selected, update its `status` to `in_progress` in `tasks.json`. If the user picked **"None"** or left all unselected, no status changes.

If no dependents exist, skip Step 4 entirely (0 prompts).

### Step 5 — Doc propagation reminder (inline text, no button)

If the completed task's title or description matches the heuristic (words like "design", "architecture", "schema", "spec", "refactor", "rewrite", or mentions structural change), print inline:

> *"Design change detected. Update any relevant `Reference/*.md` / `Documentation/md/*.md` files this session. If the project uses CPS, run `cps-refresh` before closing."*

This is a reminder, not a blocker. No `AskUserQuestion`.

### Removed from previous flow

- ❌ **Reopen gate** — COMPLETE is now authoritative. The completion log captures history. Mistakes recovered via `task ADD`.
- ❌ **Session boundary gate** — the user closes when they close.
- ❌ **Reprioritize auto-suggest** — counter still increments for HEALTH, but no prompt. Invoke REPRIORITIZE manually.
- ❌ **Sequential per-dependent impact prompts** — collapsed into one multi-select call.

---

## REPRIORITIZE

The only flow that moves tasks within the single `tasks.json` stack. Reads the full file. Invoked manually — COMPLETE no longer auto-suggests it.

### Step 1 — Strategy

Present `AskUserQuestion` with options:
- **"Dependency-first"** — sort by tier (T1 → T2 → T3 → Roadmap), then topologically by `depends_on` within each tier. Default.
- **"Tier-only"** — sort by tier alone, preserving existing order within each tier.
- **"Manual edit"** — user will reorder by hand in a follow-up turn.

Label: *"Which reprioritization strategy?"*

### Step 2 — Analyze and propose

Read `tasks.json`. Analyze dependency chains. Build the proposed order in memory.

Print the proposed order as a numbered prose list:
```
Proposed order:
1. [Title] — T1
2. [Title] — T1
3. [Title] — T2
...
```

Flag any orphaned dependencies (`depends_on` referencing titles not in the file) as warnings below the list.

### Step 3 — Confirm

Present `AskUserQuestion` with options:
- **"Apply"** — write the reordered array back to `tasks.json`.
- **"Cancel"** — discard the proposed order, no change.

Label: *"Apply this order?"*

### Step 4 — Write

On Apply: rewrite `tasks.json` with the reordered array. Update `meta.last_reprioritized` and reset `meta.completions_since_reprioritization` to 0. Update `meta.last_updated` and `meta.last_updated_note` with `"reprioritized: [strategy]"`.

**Do not write until the user confirms Apply.**

---

## REVIEW

Show a formatted summary of the full backlog. Read `tasks.json` once.

Output format:
```
## tasks.json — N total tasks

T1: [count] | T2: [count] | T3: [count] | Roadmap: [count]
Pending: [count] | In progress: [count] | Blocked: [count]

### T1
1. [Title] — [status]
2. [Title] — [status]

### T2
1. [Title] — [status]
...

### T3
...

### Roadmap
...

## Dependency Chain Issues
[any tasks with depends_on referencing non-existent titles — or "None" if clean]
```

Title + tier + status only. Do not print descriptions. Do not present an `AskUserQuestion` at the end — REVIEW is informational.

---

## HEALTH

Quick diagnostic. Read `tasks.json` once.

Check for:

1. **Description bloat** — any description > 120 chars → list them.
2. **Orphaned dependencies** — `depends_on` or `unblocks` referencing titles that do not exist in the file.
3. **Stale in_progress** — tasks marked `in_progress` with no session activity (flag for user review).
4. **File size** — if `tasks.json` exceeds 15 tasks, recommend a REPRIORITIZE + prune pass.
5. **Counter state** — show `completions_since_reprioritization` value and configured threshold. If the counter is at or over the threshold, print a one-line suggestion to run REPRIORITIZE manually (informational only, no prompt).
6. **Completion log** — if `tasks_completed.log` exists, show line count and date range covered.
7. **Tier distribution** — count per tier, flag if any tier is empty or if T1 exceeds 5 (too many architectural items in flight).

Output as a compact diagnostic. Suggest fixes but do not auto-apply. No `AskUserQuestion` — HEALTH is informational.

---

## Sub-flow invocation cheat sheet

| User intent | Sub-flow |
|---|---|
| "what should I work on" / session open | RECOMMEND |
| "add a task" / "log that" | ADD |
| "mark that done" / "I finished" | COMPLETE |
| "reprioritize" / "reorder" | REPRIORITIZE |
| "show me the backlog" / "review tasks" | REVIEW |
| "task health" / "any orphans" | HEALTH |
| RECOMMEND surfaces empty T1/T2 | EMPTY-STATE FLOW |
| User picks a roadmap item in empty state | PROMOTE FROM ROADMAP |
