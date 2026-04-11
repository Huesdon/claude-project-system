# Patch p005: CPS Task Module

**Applies to:** Core + Full
**Date added:** 2026-04-08

## Detection

Patch is PRESENT (skip) if ALL of the following are true:
- `Reference/Claude/CPS_Task_Module.md` exists
- `Reference/Claude/tasks.json` exists

If ANY check fails → patch is NEEDED.

## Actions

### 1. Create `Reference/Claude/CPS_Task_Module.md`

Write verbatim:

```markdown
# CPS Task Module — Backlog Management Standard

> Externalized from CLAUDE.md §9 to reduce per-session token cost. CLAUDE.md retains the trigger summary; this file holds the full rationale and detail.
>
> **Applies to:** Any CPS-enabled project that uses the `task` skill for cross-session backlog management.

## 1. Session Start — RECOMMEND Flow

At session start, read `Reference/Claude/tasks.json` (active T1/T2 only) and surface the top 1–3 tasks as an `AskUserQuestion` before any other work begins. Do **NOT** read `tasks_backlog.json` at startup — it contains deferred work. Trust the existing order: REPRIORITIZE produces a dependency-aware ranking, so the top of the file is already the right answer.

## 2. Task Cleanup Before Session Close (MANDATORY)

When a task is fully done, call `task COMPLETE` immediately. Completed tasks are removed from `tasks.json` and appended as a single line to `Reference/Claude/tasks_completed.log` (format: `YYYY-MM-DD | task-id | title`).

## 3. Reprioritization Counter

`tasks.json` header tracks `completions_since_reprioritization`. When it reaches **10**, prompt the user to run REPRIORITIZE and reset the counter.
```

### 2. Create `Reference/Claude/tasks.json`

Only create if it does not already exist. Write verbatim:

```json
{
  "meta": {
    "completions_since_reprioritization": 0,
    "last_reprioritized": null
  },
  "tasks": []
}
```
