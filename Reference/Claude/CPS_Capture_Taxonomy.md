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
