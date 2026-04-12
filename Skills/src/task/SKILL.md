---
name: task
description: >
  Project task backlog manager for Claude Cowork. Single source of truth at
  Reference/Claude/tasks.json holds every tier (T1, T2, T3, Roadmap). First run
  creates the file and writes the Task Module section into CLAUDE.md. Manages
  add, complete, reprioritize, review, health, recommend across all tiers in
  file order. EMPTY-STATE FLOW promotes Roadmap items to tasks, or Ideas to
  Roadmap, when tasks.json is empty or fully blocked. Every prompt uses
  AskUserQuestion; pickers use numbered buttons so long titles render. Invoke
  on "add a task", "log this as a task", "what should I work on", "reprioritize
  the backlog", "mark that done", "task backlog", "show me open tasks", "task
  status", "run task", or any new project needing structured task tracking.
---

# task — Project Task Backlog Manager

Single canonical file: `Reference/Claude/tasks.json` holds every task at every tier (T1, T2, T3, Roadmap). There is no separate backlog file. Order within the file is authoritative: REPRIORITIZE is the only way tasks move within the stack.

Completion log: `Reference/Claude/tasks_completed.log` (one line per completed task, lazy-created on first COMPLETE).

Completed tasks are removed from `tasks.json` and appended to the log.

---

## Question Route Map

Every question to the user routes through `AskUserQuestion`. Match the response condition to a row; the routing is mandatory. This route map is canonical for the project — project CLAUDE.md §0a and the memory feedback file point here. Deep reference (failure-mode catalog, worked replacements, edge cases): `Reference/Patterns/2026-04-11-question-button-routing.md`.

| Condition | Use |
|---|---|
| Picking from a list of items | `AskUserQuestion`, numbered button labels (`1`/`2`/`3`/`Show all`), full title in option description |
| Permission gate (file create / modify / delete, destructive op) | `AskUserQuestion`, two options: action verb (e.g., `Approve write`) and `Reject` |
| Binary yes/no on a clear proposition | `AskUserQuestion`, two labeled options stating both outcomes |
| Multi-choice between approaches or scopes | `AskUserQuestion`, one option per approach (2–4 options) |
| Forward-looking next-action ("ready to / want me to / should I / shall I / let me know / just say / happy to") | `AskUserQuestion`, one option per concrete next action — never `Yes / No proceed` |
| Clarifying ambiguity in the user's request | `AskUserQuestion`, one option per candidate interpretation |
| Citing a fact or framing rhetorically (no answer expected) | Prose (not a question; no `?`) |

The **Forward-looking next-action** row is the failure-mode anchor. The recurring miss is the closing prose tail — *"Done. Ready to draft X?"* / *"Want me to also update Y?"* — written as plain text instead of buttons. Any final sentence that matches that row routes to `AskUserQuestion`. No exceptions.

Test: after sending, does the user have a decision to make before work continues? Yes → `AskUserQuestion`. No → prose.

### Task-picker numbered button pattern

When picking from lists with long titles, use the numbered pattern:

1. Print numbered prose block:
   ```
   1. Grep for stale 'double-click the cmd' references — T3
   2. Remove Windows-only language from cps-init SKILL.md — T3
   3. Update cps-setup SKILL.md Step 6 wording — T3
   ```
2. Present `AskUserQuestion` with labels `1`, `2`, `3`, etc. plus `Show all`. Full title goes in the description field.

Button labels stay short. Tier/gate flows (`T1`/`T2`/`T3`/`Roadmap`, Yes/Not-yet) use natural wording — the numbered pattern is only for item lists.

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
    "reprioritization_strategy": "dependency-first",
    "flow_metrics": {
      "completions": [],
      "summary_interval": 5,
      "last_summary_at": 0
    }
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
      "started_at": "YYYY-MM-DD | null",
      "complexity": "1 | 2 | 3"
    }
  ]
}
```

**`flow_metrics.completions[]` schema:**
```json
{
  "id": "task-id",
  "tier": "T1",
  "constraint_alignment": "exploits",
  "started": "YYYY-MM-DD",
  "completed": "YYYY-MM-DD",
  "cycle_time_days": 0,
  "captures_emitted": 0,
  "complexity": 1
}
```

**Cap:** Keep most recent 50 records. Drop oldest on overflow.
**`started_at`:** Written when task status → `in_progress`. Null for tasks predating this schema.

**Tier conventions:** T1 = architectural/high design impact, T2 = subsystem, T3 = docs/polish, Roadmap = future.
**Status values:** `pending`, `in_progress`, `blocked`.
**Single-file rule:** Every tier lives in `tasks.json`. Order is maintained by REPRIORITIZE (T1 before T2 before T3 before Roadmap, dependencies before dependents within each tier). There is no `tasks_backlog.json`.
**Description rule:** One sentence, 80–120 chars. WHAT not HOW.
**`completions_since_reprioritization`:** Incremented on COMPLETE for HEALTH visibility only. COMPLETE does not auto-prompt REPRIORITIZE.

---

## Token Discipline

**Hard cap: 15 tasks max loaded per operation.** RECOMMEND reads first 15 only (priority-sorted); REPRIORITIZE/REVIEW/HEALTH read full file.

- Read once per operation, parse only needed fields.
- For ADD/COMPLETE/RECOMMEND: read → change in memory → write once.
- Never re-read already-loaded files.

---

## Log Access Routing

`Reference/Claude/tasks_completed.log` grows unbounded. Use the row that matches the operation; the absence of a "Read full log" row is intentional.

| Operation | Use |
|---|---|
| Append a completion line | `python -c "open('Reference/Claude/tasks_completed.log','a').write('YYYY-MM-DD \| id \| Title\n')"` (creates file on first call) |
| Get line count | `wc -l Reference/Claude/tasks_completed.log` |
| Get most recent completion date | `tail -1 Reference/Claude/tasks_completed.log \| cut -d'\|' -f1` |
| Strip log line on Reopen | `sed -i '$d' Reference/Claude/tasks_completed.log` (only valid for the line appended in the current turn) |

Reference: `Reference/Patterns/2026-04-11-positive-routing-tables.md`.

---

## Capture Batching (Rule 2 + Rule 3)

Mid-task capture candidates are batched in session scratch and surfaced once at COMPLETE. This collapses N self-trigger gates into 1 multi-select prompt.

### Session scratch file

Path: `capture_candidates.json` in the session working directory (e.g., `/sessions/<id>/capture_candidates.json`). Ephemeral — dies with session.

Schema:
```json
[
  {
    "summary": "One-line capture candidate description",
    "bucket_hint": "Pattern | Decision | Lesson | Idea | Roadmap | Documentation",
    "context": "Brief context (2-3 sentences max) preserving the *why*"
  }
]
```

### Append operation

When Claude identifies a capture candidate mid-task (self-trigger gate passes in `cps-capture`), append to `capture_candidates.json` instead of prompting. Print one silent confirmation line:

> *Batched capture candidate: "[summary]" ([bucket_hint])*

No `AskUserQuestion`. No `cps-capture` invocation. The file is read-then-written (create if absent, append to array if present).

### Flush operation (COMPLETE Step 2.5)

Read `capture_candidates.json`. If empty or absent → skip. If non-empty:

1. Print numbered list of candidates:
   ```
   Batched captures from this task:
   1. [summary] — [bucket_hint]
   2. [summary] — [bucket_hint]
   ```

2. Present `AskUserQuestion` (multi-select). Options:
   - If ≤3 candidates: one option per candidate (label = number, description = summary + bucket).
   - If 4+ candidates: top 3 by array order + **"Select all"** (description = "Capture all N candidates").
   - Always include **"Skip all"** (description = "Discard batched candidates").

3. For each selected candidate: invoke `cps-capture` with the summary and bucket_hint as context. Run sequentially (each capture is a full cps-capture flow).

4. Delete `capture_candidates.json` after processing (whether captures ran or were skipped).

---

## Auto-Sort (silent REPRIORITIZE)

Fires automatically after COMPLETE Step 2 and after ADD write. No gate, no print, no user prompt.

**Logic:** Sort `tasks` array by tier (T1 → T2 → T3 → Roadmap), then topologically by `depends_on` within each tier, then by constraint alignment (`elevates` > `exploits` > `subordinates` > unset) at the same dependency level. Same algorithm as REPRIORITIZE Step 1.

**Triggers:**

| Signal | When it fires |
|---|---|
| COMPLETE Step 2 | After counter increment, before capture batch gate |
| ADD | After append + write |
| REFRAME | After `current_constraint` changes in meta |

**Write:** Rewrite `tasks.json` with sorted array in-place. Do not update `meta.last_reprioritized` or reset counter (those are manual REPRIORITIZE only).

**Manual REPRIORITIZE** remains available for alternate strategies (tier-only, manual reorder) and for explicit user-requested reorders.

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

At session start, read `Reference/Claude/tasks.json` and surface the top 1–3 actionable tasks (any tier) via `AskUserQuestion` before any other work begins. Trust the existing order: REPRIORITIZE produces a dependency-aware ranking across every tier, so the top of the file is already the right answer regardless of tier. Wait for user confirmation before starting.

**Button rendering rule:** Task-picker flows use a numbered prose list plus number-only button labels (`1` / `2` / `3` / `Show all`) so long titles never break rendering. The full title appears in the option description, not the button label.

**WIP cap = 1:** At most one task may be `in_progress` at any time. Check for in-progress tasks (Step 2a) before surfacing new picks. Options: mark complete, keep working, or park and switch. RECOMMEND refuses to admit a second task while one is active.

**Before surfacing tasks:** Check for in-progress tasks (Step 2a) and for invalid `"completed"` status values (Step 2b). Resolve both before picking new work.

**Empty state:** If there are no actionable tasks at any tier (file empty or every task blocked), run the EMPTY-STATE FLOW to surface Roadmap items to promote to tasks, or Ideas to promote to the Roadmap.

**Cross-session signal:** When the user selects a task, immediately write `status: "in_progress"` for that task before starting work. This is what Step 2a detects next session.

### Immediate Completion (MANDATORY)

When a task is fully done — all steps finished, files written, docs propagated — call `task COMPLETE` immediately. Do **not** wait for session close or explicit user instruction. COMPLETE is write-first: the task is removed from `tasks.json` and a line is appended to `tasks_completed.log` **before** any prompt appears. Never leave a finished task in `pending` or `in_progress` between work items — `tasks.json` must stay in sync with reality at all times.

### Capture Batching at COMPLETE (Rule 2 + Rule 3)

Mid-task capture candidates are batched in session scratch (`capture_candidates.json`) and surfaced as one multi-select `AskUserQuestion` at COMPLETE, after the task is committed closed. This collapses N self-trigger gates into 1 prompt. User-invoked captures ("capture this") bypass batching and run immediately. See the `cps-capture` skill for batch-mode routing.

### Terminal Menu (post-close action picker)

After the write, COMPLETE always issues a single `AskUserQuestion` terminal menu with up to 4 options: **Next: [unblocked dependent]** · **Next: [second slot]** · **Close session** · **Reopen [Title]**. The menu is a post-close action picker, not a gate to closure — the task is already committed closed when the menu appears. Picking **Next:** sets that task's `status` to `in_progress`. Picking **Close session** is the clean exit (no further writes). Picking **Reopen** is an explicit revert: it restores the task to `in_progress`, strips the completion log line, and decrements the counter. Single-focus invariant: the menu promotes at most one task.

### Reprioritization

REPRIORITIZE is invoked manually when the user wants it. The meta counter `completions_since_reprioritization` is still incremented on every COMPLETE so HEALTH can surface it, but COMPLETE no longer auto-prompts to run REPRIORITIZE. Run it on demand: *"reprioritize"* / *"reorder the backlog"*.

### Keep tasks.json Current

`Reference/Claude/tasks.json` is the cross-session task backlog and the single source of truth. When new work is discovered mid-session — either by Claude noticing a follow-up or by the user mentioning something — call `task ADD` immediately rather than mentioning it in chat and forgetting. Treat user-added entries as authoritative: do not second-guess priority, retitle, or reorder them without explicit instruction.

### Propagate Design Changes to Documentation Same-Session

After any design decision or architectural change, update all relevant `Reference/*.md` and `Documentation/md/*.md` files in the same session. Create a new Reference doc if none exists for the topic. Do not close a session with design decisions captured only in `tasks.json` or session memory — they must be fully encoded in documentation files.

If the project uses CPS (Claude Project System), CPS indexes these docs; stale docs mean stale query results. **After doc updates, run `cps-refresh` to re-index changed files before session close.**
```

Surface: "Backlog initialized. Task Module section written to CLAUDE.md."

---

## RECOMMEND (session startup)

**Token budget: minimal.** This runs on every session open.

1. Read `Reference/Claude/tasks.json` only. Parse tasks array. If more than 15 tasks, truncate to first 15 (they are priority-sorted).

### Step 1b — Constraint line (Rule 6)

Print one line before any picks or checks:

> *"Current constraint: [current_constraint] — top tasks aligned ↑"*

Read `current_constraint` from `tasks.json` meta. If absent, print: *"No constraint set — run constraint identification."* If `constraint_modifier` is present, append it in parentheses: *"Current constraint: attention (decision-bandwidth) — top tasks aligned ↑"*.

This line is informational prose (no `AskUserQuestion`). It fires every session as the first visible output of RECOMMEND.

### Step 1c — Flow summary (periodic)

Check `flow_metrics.completions.length` vs `flow_metrics.last_summary_at`. If `completions.length - last_summary_at >= summary_interval`, print one summary line:

> *"Flow (last N): avg cycle [X] days, [Y]% constraint-aligned (elevates+exploits)."*

Compute from the most recent `summary_interval` entries. Update `last_summary_at` to current `completions.length`. One line only — do not expand into a table or detailed breakdown.

### Step 2a — In-progress check (WIP cap = 1)

If any task has `"status": "in_progress"`, ask via `AskUserQuestion`:

- **"Mark complete"** — run COMPLETE (remove + log), continue to Step 3.
- **"Keep working"** — surface as sole recommendation, skip to Step 5. No second task admitted.
- **"Park and switch"** — set task `status` back to `"pending"`, write `tasks.json`, continue to Step 3 (pick new task). Parked task retains its file-order position.

Label: *"'[Title]' is in progress — WIP cap is 1."*

**WIP invariant:** At most one task may have `status: "in_progress"` at any time. RECOMMEND refuses to surface new picks while an in_progress task exists. The three options above are the only exits.

### Step 2b — Invalid status guard

If any task has `"status": "completed"` (invalid — must be removed on completion), ask via `AskUserQuestion`:

- **"Remove and log it"** — run COMPLETE (remove + log).
- **"Reopen as pending"** — set `status: "pending"` and write.

Label: *"'[Title]' has status 'completed' but was never removed from tasks.json — fix it now?"*

### Step 3 — Filter and pick

Filter remaining: skip `blocked`. RECOMMEND surfaces all tiers in file order (REPRIORITIZE owns ranking). Select top 1–3 by position. Extract: `title`, `tier`, `status` only.

### Step 4 — Present (numbered button pattern)

Print numbered list:
```
1. [Title] — [tier]
2. [Title] — [tier]
3. [Title] — [tier]
```

Present `AskUserQuestion` with up to 4 options. Label `1`/`2`/`3` with descriptions = full titles. Add `Show all` → "See every task in tasks.json across all tiers". Only include numbers that match real candidates.

### Step 5 — Mark in progress

On selection → immediately write `status: "in_progress"` and `started_at: "[today]"` for that task to `tasks.json` before starting work (cross-session signal for Step 2a; `started_at` feeds flow metrics cycle_time).

On `Show all` → run REVIEW flow.

### Step 5b — Plan buffer pre-stage (Rule 5)

After marking in_progress, spawn a Haiku agent to pre-load prior art for the selected task. This runs before Sonnet enters plan mode.

**Trigger:** Fires on every task start (Step 5 completes).

**Mechanism:**

1. Extract keywords from the task's `title` + `description` (strip stop words, keep nouns/verbs).
2. Spawn Haiku agent with prompt: *"Run `cps-query` with query '[keywords]'. Return up to 10 hits as a markdown list: `- [doc title](path) — relevance snippet`. Write results to `/sessions/<id>/plan_buffer.md`."*
3. If `.cps/cps_server.py` does not exist (CPS not installed), skip silently. Write empty `plan_buffer.md` with `*No CPS runtime — plan buffer skipped.*`

**Fallback:** If Haiku agent fails or times out, proceed without plan_buffer.md. Sonnet falls through to manual `Reference/Patterns/_INDEX.md` + `Reference/Decisions/_INDEX.md` reads per §0b routing table.

**Consumer:** When entering plan mode (any `ExitPlanMode` draft), read `plan_buffer.md` if present. Cite staged hits in the plan alongside pattern/decision index reads.

**Format of `plan_buffer.md`:**
```
# Plan Buffer — [Task Title]
Staged: [today]

- [doc title](relative/path) — one-line relevance snippet
- [doc title](relative/path) — one-line relevance snippet
...
```

Cap: 10 hits max. Session-scoped (ephemeral).

### Empty state

If Step 4 yields 0 candidates → run **EMPTY-STATE FLOW**.

Fast pick-list only: do not read full descriptions or dependency chains.

---

## EMPTY-STATE FLOW

Triggered when `tasks.json` is empty or every task is `blocked`. Surfaces Roadmap → Ideas chain.

### Step 1 — Check Roadmap

Glob `Reference/Roadmap/*.md` (exclude `_INDEX.md`).

**If roadmap files exist:**

1. Read `Reference/Roadmap/_INDEX.md` for titles (format: `- [Title](file.md) — hook`).
2. Extract top 3 titles.
3. Print numbered list:
   ```
   1. [Title 1] — [hook]
   2. [Title 2] — [hook]
   3. [Title 3] — [hook]
   ```
4. Present `AskUserQuestion` with options `1`/`2`/`3`/`Skip for now`.

   Label: *"tasks.json has no actionable work. Promote a roadmap item?"*

5. On number → run **PROMOTE FROM ROADMAP**.
6. On `Skip for now` → end (do not auto-surface Ideas).

**If no roadmap files → Step 2.**

### Step 2 — Check Ideas

Glob `Reference/Ideas/*.md` (exclude `_INDEX.md`).

**If idea files exist:**

1. Read `Reference/Ideas/_INDEX.md` for titles.
2. Extract top 3.
3. Print numbered list.
4. Present `AskUserQuestion` with options `1`/`2`/`3`/`Skip for now`.

   Label: *"Roadmap empty. Promote an idea to the roadmap?"*

5. On number → tell user:

   > *"To promote '[title]' to Roadmap, run `cps-capture` and say 'promote [title] to roadmap'. Then come back here to convert it to a task."*

6. On `Skip for now` → end.

**If no idea files:**

Say: *"Backlog, roadmap, and ideas empty. Use `task ADD` to add directly, or `cps-capture` to save an idea/roadmap item."*

---

## PROMOTE FROM ROADMAP

Triggered when user selects a roadmap item to convert to active task.

### Step 1 — Locate the roadmap file

Glob `Reference/Roadmap/*.md` (exclude `_INDEX.md`). Find file matching selected title (fuzzy slug). Read it.

If not found: ask user to confirm filename from numbered list.

### Step 2 — Extract task fields

Read from roadmap file:
- **Title** — `# Title` heading.
- **Goal** — `## Goal` section (one sentence) → becomes task description.
- **Horizon** — `Now | Next | Later` from frontmatter → tier hint: `Now` → T1, `Next`/`Later` → T2.

### Step 3 — Confirm task fields

Present `AskUserQuestion` (worded options, not numbered):

- **"T1 — Architectural"** — promote as T1 with Goal as description.
- **"T2 — Subsystem"** — promote as T2 with Goal as description.
- **"Edit before adding"** — user provides custom title/description next.

Label: *"Promoting '[title]' from Roadmap. Confirm tier?"* (Print Goal in prose above.)

On `Edit before adding`: ask for title and description via free-text (NOT `AskUserQuestion`).

### Step 4 — Add the task

Run ADD flow with confirmed fields:
- `title` = roadmap file title.
- `tier` = T1 or T2 (from Step 3).
- `description` = Goal sentence (trimmed to 80–120 chars).
- `depends_on` = [] (narrative only, don't carry over).
- `status` = `pending`.

Write to `tasks.json` via ADD logic.

### Step 5 — Update the roadmap file status

Edit roadmap file: replace `**Status:** Active` with `**Status:** Promoted`.

If CPS present (`.cps/cps_server.py` exists), run:
```bash
python .cps/cps_server.py ingest --files=<roadmap_file_path>
```

### Step 6 — Report and offer immediate start

Report: `Promoted '[title]' from Roadmap → added as [tier] task in tasks.json.`

Present `AskUserQuestion`:
- **"Yes, set to in_progress"** — update task status to `in_progress`.
- **"Leave as pending"** — no change.

Label: *"Start working on it now?"*

---

## ADD

Extract from context. Ask only for missing required fields via `AskUserQuestion`.

| Field | Required | Notes |
|-------|----------|-------|
| title | Yes | Verb + noun ("Build login page"). |
| tier | Yes | T1 / T2 / T3 / Roadmap. |
| description | Yes | One sentence, 80–120 chars. |
| depends_on | No | Array of task titles. |
| unblocks | No | Array of task titles. |
| complexity | Yes | 1 = simple, 2 = moderate, 3 = complex. Infer from tier if obvious (T3 → 1, T1 → 2–3). |

If tier missing: present `AskUserQuestion` with **"T1 — Architectural"** / **"T2 — Subsystem"** / **"T3 — Docs/Polish"** / **"Roadmap — Future"**.

If complexity missing: present `AskUserQuestion` with **"1 — Simple"** / **"2 — Moderate"** / **"3 — Complex"**.

Generate `id` as `[tier]-[slug]` (e.g., `t2-help-system`). Set `status: "pending"`.

Read `tasks.json` → parse → append → write. Update `meta.last_updated` and `meta.last_updated_note`.

Append to end, then run **Auto-Sort** to place in optimal order (tier → dependency → constraint alignment).

---

## COMPLETE

Write-first, terminal-menu. Happy path: 1 prompt (menu) with no batched captures. With batched captures: 1 multi-select + sequential cps-capture runs + menu. Menu always runs last.

**Ordering:** All writes happen in Steps 1–2 before any prompt. Menu is post-close action picker. Reopen is post-close revert.

### Step 1 — Remove and log (MANDATORY)

Read `tasks.json` → find task by title (case-insensitive substring) → capture `id`, `title`, `tier`, `depends_on` → remove from array → write.

Update `meta.last_updated` (today) and `meta.last_updated_note` (`"completed: [Title]"`).

Append a completion line via the **Append a completion line** row in **Log Access Routing**. Lazy-create is handled by the append mechanism.

### Step 2 — Counter increment (MANDATORY)

Increment `meta.completions_since_reprioritization` by 1 (HEALTH visibility only).

### Step 2a — Auto-sort (MANDATORY)

Run **Auto-Sort** on the remaining tasks array. This ensures the terminal menu's "Next:" picks reflect optimal order after the completed task is removed.

### Step 2b — Record flow metric (MANDATORY)

Append a record to `meta.flow_metrics.completions[]`:

- `id`: task id (captured in Step 1)
- `tier`: task tier
- `constraint_alignment`: task's alignment value (or `null`)
- `started`: task's `started_at` value (or `null` if predates schema)
- `completed`: today's date
- `cycle_time_days`: integer diff between `started` and `completed` (or `null`)
- `captures_emitted`: length of `capture_candidates.json` array (0 if absent)
- `complexity`: task's `complexity` value (or `null` if predates schema)

If `completions.length > 50`, drop the oldest entry before appending.

Initialize `flow_metrics` in meta if absent (schema migration): `{"completions": [], "summary_interval": 5, "last_summary_at": 0}`.

### Step 2.5 — Capture batch gate (Rule 2 + Rule 3)

Run the **Flush operation** from the Capture Batching section. This happens after the task is committed closed (Steps 1–2) but before the terminal menu. If no candidates are batched, this step is invisible.

### Step 3 — Silent scans

Run in memory (no prompts). Feed results to Step 5 menu.

- **Impact scan:** Scan `tasks.json` for tasks with completed title in `depends_on`. Collect up to 2 unblocked dependents by file order → first "Next:" candidates.
- **RECOMMEND fill:** Run RECOMMEND Steps 3–4 on remaining file. Collect until combined "Next:" slot count = 2 (deduped vs. impact scan). If empty: fallback to collapse rules.
- **Doc-change heuristic:** Check if completed title/description matches `design|architecture|schema|spec|refactor|rewrite`. Flag for summary.

### Step 4 — Terminal menu (MANDATORY)

Print one-line summary:
> Completed **[Title]**. Counter N/M.[ Unblocked: title1, title2.][ Design change — update Reference/ docs.]

Omit Unblocked if no dependents. Omit design-change if heuristic false.

Issue **one** `AskUserQuestion` call. Header: `Next action`. Build up to 4 options (priority order):

1. **Next: [title]** — first unblocked dependent (if found). Description = full title + tier. Pick → set `status: "in_progress"`.
2. **Next: [title]** — second unblocked OR top RECOMMEND pick. Same on pick.
3. **Close session** — no writes. Clean close.
4. **Reopen [Title]** — restore to `in_progress`, strip log line via the **Strip log line on Reopen** row in **Log Access Routing**, decrement counter. Stop.

**Collapse (fewer than 2 candidates):**
- One: `Next: A` + `Close session` + `Reopen [Title]` (3 options).
- Zero (empty): `Close session` + `Reopen [Title]` (2 options). Remind user to run EMPTY-STATE FLOW next session.

**Single-focus:** Pick at most one task to `in_progress`. Other unblocked stay `pending` (user can start via RECOMMEND). Do not multi-select.

**Resolution:**
- **Next: picked** → write `status: "in_progress"`. Session boundary: user may close or continue inline.
- **Close session** → no writes. Stop.
- **Reopen** → revert Phase 1. Stop. Do not re-surface menu.

---

## REPRIORITIZE

Only flow that moves tasks within `tasks.json`. Reads full file. Default strategy: dependency-first. Invoked manually or by free-text override (e.g., "reprioritize tier-only").

### Step 1 — Analyze, sort, and print

Read `tasks.json`. Sort by tier (T1 → T2 → T3 → Roadmap), then topologically by `depends_on` within each tier.

**Constraint-aligned weighting:** Read `current_constraint` from meta. Within each tier, after topological sort by `depends_on`, apply a secondary sort: tasks with `constraint_alignment` of `elevates` or `exploits` sort above tasks with `subordinates` at the same dependency level. Tasks without `constraint_alignment` sort after `subordinates`.

Print applied order with alignment annotation:
```
Applied order:
1. [Title] — T1 (elevates)
2. [Title] — T1 (exploits)
3. [Title] — T1 (subordinates)
4. [Title] — T2 (elevates)
...
```

Flag orphaned dependencies (`depends_on` not in file) as warnings.

**Free-text override:** If user specifies "tier-only", sort by tier alone, preserve in-tier order. If "manual", print current order and let user reorder by hand.

### Step 2 — Write (auto-apply)

Rewrite `tasks.json` with the sorted array. Update `meta.last_reprioritized` and reset `meta.completions_since_reprioritization` to 0. Update `meta.last_updated` and `meta.last_updated_note` with `"reprioritized: dependency-first"`.

No confirmation gate. User can object inline after seeing the printed order — revert by requesting a different strategy.

---

## REVIEW

Show formatted summary of full backlog. Read `tasks.json` once.

Output:
```
## tasks.json — N total tasks

T1: [count] | T2: [count] | T3: [count] | Roadmap: [count]
Pending: [count] | In progress: [count] | Blocked: [count]

### T1
1. [Title] — [status]
2. [Title] — [status]

### T2
...

### T3
...

### Roadmap
...

## Dependency Chain Issues
[orphaned depends_on — or "None" if clean]
```

Title + tier + status only. No descriptions. No `AskUserQuestion` (informational).

---

## HEALTH

Quick diagnostic. Read `tasks.json` once.

Check:

1. **Description bloat** — any description > 120 chars.
2. **Orphaned dependencies** — `depends_on` or `unblocks` referencing non-existent titles.
3. **Stale in_progress** — tasks marked `in_progress` with no recent activity.
4. **File size** — if > 15 tasks, suggest REPRIORITIZE + prune.
5. **Counter state** — show `completions_since_reprioritization` vs. threshold. If at/over, suggest REPRIORITIZE manually (info only).
6. **Completion log** — if exists, report line count and most recent date via the **Get line count** and **Get most recent completion date** rows in **Log Access Routing**.
7. **Tier distribution** — count per tier. Flag if empty or T1 > 5.

Output as compact diagnostic. Suggest fixes but no auto-apply. No `AskUserQuestion` (informational).

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
| Zero actionable tasks at any tier | EMPTY-STATE FLOW |
| User picks roadmap item in empty state | PROMOTE FROM ROADMAP |
