# Lean Session Close Routine

**Captured:** 2026-04-08
**Applies to:** All CPS projects; any session where Claude is wrapping up.

## Context
Session close routines were burning 5+ minutes on ceremony: mid-session task mutations, a "shipped / state / next session" prose recap, TodoWrite reset, and new continuation tasks with 200-word descriptions embedded in tasks.json. The user already has tasks.json as source of truth — reading it back in prose duplicates what they can see directly.

## Technique
At session end, do exactly four things in order:
1. Present any unshipped `.skill` files via `mcp__cowork__present_files`.
2. One Haiku call (Tier 1) that batches every tasks.json mutation for the session — COMPLETE marks, new ADDs, meta bumps — into a single delegation.
3. Write a 2-line close message in this format: `Shipped: X, Y. Next: <one-line next step>.`
4. Stop.

Do not recap session work. Do not read tasks.json state back to user. Do not reset TodoWrite (let todos die with the session). New continuation tasks get a one-line title in tasks.json; any detail goes in a scratchpad note in `Reference/Claude/`, not embedded in description fields.

## When to use
- User says "wrap", "close", "end session", "slim it down" at the end of a workstream.
- A task chain hits a natural stopping point and suggests a session boundary.
- A session boundary suggestion was explicitly accepted.

## When NOT to use
- Mid-workstream. This is a close routine, not a progress checkpoint.
- When multiple tasks are still in flight and the user hasn't decided scope. Finish the decision first, close second.
- When the session produced zero file mutations and zero task completions — there's nothing to batch, so just stop.

## Examples
**Good close:** Present cps-setup.skill and cps-init.skill. One Haiku call marks two tasks complete and adds one continuation task. "Shipped: cps-setup.skill, cps-init.skill. Next: `task RECOMMEND` picks up the in-session sim." Done.

**Bad close (this session, pre-rule):** Present files, three separate Haiku calls (rebundle × 2 + tasks.json mark-complete), a 15-line shipped/state/next-session recap table, a todo reset, then another 100 words of context. Five minutes of ceremony after the real work ended.
