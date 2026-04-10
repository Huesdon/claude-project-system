# p001 — Ideas + Roadmap Knowledge Buckets

**ID:** `p001-ideas-roadmap`
**Profile:** Both (Core and Full)
**CPS version introduced:** Phase 8.7

Detection checks are in `patch-index.md`. This file contains only the actions.

---

## Actions (apply in order)

### Action a — Create `Reference/Ideas/` and `Reference/Ideas/_INDEX.md`

Skip if `Reference/Ideas/_INDEX.md` already exists.

Create the directory (if needed) and write the file with this exact content:

```
# Ideas Index

Nascent ideas, exploration candidates, and "what if" items. Capture early, promote when ready.
Use `cps-capture` with trigger "add idea". Promote to Roadmap with "promote [title] to roadmap".

<!-- entries below -->
```

### Action b — Create `Reference/Roadmap/` and `Reference/Roadmap/_INDEX.md`

Skip if `Reference/Roadmap/_INDEX.md` already exists.

Create the directory (if needed) and write the file with this exact content:

```
# Roadmap Index

Committed intentions, not yet active tasks. Each item has a goal, rationale, and horizon (Now/Next/Later).
Use `cps-capture` with trigger "add to roadmap". Promote to tasks with "promote [title] to tasks".

<!-- entries below -->
```

### Action c — Update CLAUDE.md §12

Skip if CLAUDE.md §12 already contains "Ideas" and "Roadmap".

Find the `## 12. Knowledge Capture` section. It ends at the next `##` heading or EOF. Replace only that section (preserve everything before and after it) with:

```
## 12. Knowledge Capture — Taxonomy

Five buckets under `Reference/`: Patterns, Decisions, Lessons, Ideas (low-friction, promote when ready), Roadmap (committed intentions with Now/Next/Later horizon). Self-trigger gate requires all four capture criteria (Ideas have a lower bar — "what if" thoughts welcome). Promotion flow: Idea→Roadmap→Tasks.
Full spec: `Reference/Claude/CPS_Capture_Taxonomy.md`.
Trigger phrases: "add idea", "add to roadmap", "promote [title] to roadmap", "promote [title] to tasks".
```

If no §12 section exists but CLAUDE.md exists: append the section above before the final `---` separator, or at EOF if no separator exists.

If no CLAUDE.md exists at all: skip this action and note it in the report.

### Action d — Update `Reference/Claude/CPS_Capture_Taxonomy.md`

Skip if the file doesn't exist (don't create it from scratch).
Skip if the file already contains `<!-- rev: 2 -->`.

Replace the entire file contents with the canonical five-bucket version:

```
<!-- rev: 2 -->
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
- **Idea → Roadmap:** "promote [title] to roadmap" — creates a Roadmap entry referencing the source idea; updates idea's Status to "Promoted".
- **Roadmap → Tasks:** "promote [title] to tasks" — spawns task entries in `Reference/Claude/tasks.json`; updates roadmap item's Status to "Promoted". (Handled by the `task` skill promotion command.)

**Claude-initiated capture (self-trigger).** Claude proactively flags a candidate mid-conversation when all four of these are true:
1. The knowledge is reusable across future sessions or projects
2. A future Claude would miss it if not captured
3. The *why* can be stated in one sentence
4. There is a clear bucket fit (Pattern / Decision / Lesson / Idea / Roadmap)

For **Ideas**, the self-trigger bar is lower: flag if something surfaces that seems worth exploring but isn't ready to be a task — "what if" thoughts with enough specificity to be worth tracking.

When Claude flags a candidate, it pauses, states it in one line, and asks "worth capturing?" before writing. Max one self-trigger prompt per ~5 exchanges to avoid interview mode.

**Pre-design retrieval (read trigger).** Before starting any design activity — new skill build, schema change, CLAUDE.md structural edit, or architecture decision — query the second brain for relevant prior knowledge. If the CPS server is available, run `cps-query` across all five buckets for the relevant domain. If CPS is not running, scan each bucket's `_INDEX.md` for relevant titles and pull any hits. Surface findings before proposing an approach.

**Capture flow:** User or Claude flags → Claude drafts content → Haiku (Tier 4) writes files + updates _INDEX.md → `cps-refresh` auto-runs → indexed.

**After capture:** If significant enough that future sessions must not miss it, suggest adding a pointer to this CLAUDE.md — but do not edit without explicit user approval.
```

### Action e — Update `cps_config.json` source_paths (Full profile only)

Skip if profile is Core.
Skip if `.cps/cps_config.json` doesn't exist.
Skip if `source_paths` already contains entries for `Reference/Ideas` and `Reference/Roadmap`.

Read `.cps/cps_config.json`. Find the `source_paths` array. Add these two entries if missing:
- `"Reference/Ideas/**/*.md"`
- `"Reference/Roadmap/**/*.md"`

Write the updated JSON back in place. Preserve all other fields exactly.
