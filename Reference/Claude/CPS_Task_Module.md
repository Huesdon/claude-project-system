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

When a task is fully done, call `task COMPLETE` immediately — do not wait for session close. Completed tasks are removed from `tasks.json` and appended as a single line to `Reference/Claude/tasks_completed.log` (format: `YYYY-MM-DD | task-id | title`). Do not leave checkmark stubs or strikethrough entries in `tasks.json` — they burn tokens on every future RECOMMEND pass. The log preserves history without bloating the active backlog.

After marking complete, present a two-option `AskUserQuestion`: **"Confirmed complete"** (proceed to next work) or **"Reopen it"** (restore to `in_progress`, undo the log entry). Never leave a finished task in active state between work items.

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
