# Instruction Architecture

> **Last Updated:** 2026-04-08
> **Purpose:** Single source of truth for where Claude's operating rules live, why they live there, and how to add new rules without creating duplication.
> **Scope:** Applies to Shane's Cowork sessions across all projects (CPS, D3, DQR, etc.).

---

## 1. The Three-Layer Model

Claude's behavior is governed by three instruction layers, loaded in this order on every session:

| Layer | Source | Load mechanism | Scope | Edit cost |
|-------|--------|----------------|-------|-----------|
| **L1 — Preferences** | Senior Coworker Mode (settings) | Auto-loaded into system prompt every turn | All projects, all sessions | User must paste into settings UI |
| **L2 — Project CLAUDE.md** | `<project>/CLAUDE.md` and `~/.claude/CLAUDE.md` | Auto-loaded when working in that project's directory | Per-project | Direct file edit |
| **L3 — Auto-memory** | `.auto-memory/MEMORY.md` + linked files | MEMORY.md always loaded; linked files loaded on-demand when relevant | Cross-project but conditional | Direct file edit |

**Key property:** L1 and L2 are *unconditional* (always present). L3 is *conditional* (MEMORY.md is always present but the linked files are read only when triggered). This is the foundation of the dedup principle below.

---

## 2. The Dedup Principle

**One rule, one home.** A rule lives in exactly one layer. Other layers may reference it but never restate it.

**Routing question:** "Does this rule need to be active in every session, every turn, regardless of project?"

- **Yes, universally** → L1 Preferences. (Examples: Haiku delegation, brevity, permission-first, token hygiene.)
- **Yes, but only in this project** → L2 Project CLAUDE.md. (Examples: CPS module table, DQR forbidden terms, project-specific architecture rules.)
- **Conditionally, based on context the prefs can't see** → L3 Memory. (Examples: "Run RECOMMEND when CLAUDE.md has a §9 Task Module", drift-incident enforcement hooks, user-role facts.)

**Failure mode to avoid:** Memory files that re-derive the preferences. If a memory file restates a tier table, a routing heuristic, or a brevity rule that already exists in preferences, it's duplication and should be cut to just the *enforcement hook* — the part that triggers the rule, not the rule itself.

---

## 3. Rule-to-Home Map

Authoritative table. Update this row when any rule moves between layers.

| Rule | Home | Why this layer |
|------|------|----------------|
| Permission-first (ask before file create/edit) | L1 §I | Universal, every project |
| Skills folder is read-only | L1 §I | Universal infrastructure constraint |
| Token hygiene (precision tooling, parallelism) | L1 §II | Universal cost rule |
| Session limit ~15 exchanges | L1 §II | Universal cost rule |
| PDF → text via pdftotext for analysis | L1 §II | Universal cost rule |
| Haiku delegation tier model + routing heuristic | L1 §III.1 | Universal, must be active every turn |
| Haiku call protocol (model: haiku, minimal context) | L1 §III.1 | Universal, must be active every turn |
| Haiku tier recipes table | L1 §III.1 | Universal reference |
| Sonnet/Opus reservation list | L1 §III.1 | Universal, must be active every turn |
| Response brevity (terse gates, no recaps) | L1 §IV *(new)* | Universal, must be active every turn |
| Haiku pre-flight check (Q1/Q2 enforcement) | L3 `feedback_haiku_delegation_strict.md` | Enforcement hook for L1 rule — incident-driven |
| Haiku drift recovery (name it, don't hide it) | L3 `feedback_haiku_delegation_strict.md` | Enforcement hook for L1 rule — incident-driven |
| Session-start Haiku-check reminder | L3 `feedback_haiku_delegation_strict.md` | Enforcement hook for L1 rule — incident-driven |
| Session start = run RECOMMEND | L3 `feedback_session_start_recommend.md` | Conditional on §9 Task Module presence |
| User role / profile facts | L3 user_*.md | Conditional, learned over time |
| CPS module table, runtime files, phase history | L2 CPS CLAUDE.md | Project-specific |
| CPS task module §9 standard | L2 CPS CLAUDE.md | Project-specific scaffold |
| DQR forbidden terms, module reference | L2 (global) DQR section | Project-specific |

---

## 4. How to Add a New Rule

1. **Ask the routing question** (§2). Pick the layer.
2. **Search for duplicates** in the other two layers before writing. If a related rule already exists, extend it in place rather than creating a new file.
3. **Update the rule-to-home map** in §3 of this doc *in the same session* you add the rule. The map is the registry — if a rule isn't in the map, it doesn't exist.
4. **Run `cps-refresh`** so the new rule is queryable.

---

## 5. How to Retire a Rule

1. Delete the rule from its home layer.
2. Delete the row from §3 of this doc.
3. If the rule was in L3, remove the line from `MEMORY.md`.
4. Run `cps-refresh`.

Do not leave strikethrough or "deprecated" entries in active files. A retired rule is a deleted rule. History lives in git, not in the active rulebook.

---

## 6. Why This Architecture Matters

The cost of a duplicated rule is paid every turn the duplicates load. The cost of a missing enforcement hook is paid every time Claude drifts. The cost of a rule in the wrong layer is paid as either silent inactivity (rule in L3 when it should be L1) or blast-radius bugs (rule in L1 when it should be L2).

This doc exists because on 2026-04-08 the user identified that the same rules were appearing in 2-3 places, that the brevity rules were sitting in memory when they should have been in preferences, and that the Haiku enforcement hooks were buried under 30+ lines of tier re-statements that already lived in preferences. The fix was structural, not editorial: pick the right layer for each rule and let the other layers reference it.

**Maintenance signal:** If a future session adds a memory file longer than ~30 lines, that's a smell — check whether most of it should have gone into preferences instead.
