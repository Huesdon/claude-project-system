# CPS Integration Spec — Persona Startup Scans

> **⚠ HISTORICAL — Phase 5-era design doc (EM proving ground).**
> This spec describes CPS as an *acceleration layer* for persona startup scans. It predates the unified four-module definition (Knowledge / Tasks / Docs / Sessions) adopted in rev 4 of the project `CLAUDE.md`. The tier model, token savings numbers, and EM wiring below remain accurate for the Full-profile engine, but CPS is no longer framed as "just" a context-priming layer. For the current canonical definition see `CLAUDE.md` §2 and `Reference/CPS_Design.md`.
>
> **Version:** 1.0
> **Last Updated:** 2026-04-07
> **Status:** Historical / Phase 5-era design (superseded framing, still-accurate internals)
> **Depends on:** CPS Phases 1–4 (complete), EM CLAUDE.md v2.3+

---

## 1. Purpose

Define how the Context Priming System (CPS) integrates into persona startup scans to reduce token consumption. CPS is an **acceleration layer**, not a replacement — every CPS-enhanced path has a direct-read fallback. A persona works identically whether CPS is warm, cold, or absent.

---

## 2. Design Principles

**P1 — Zero degradation.** CPS unavailable = existing scan runs unchanged. No new failure modes.

**P2 — Cache-first, file-fallback.** Tier 2 queries hit the semantic cache before reading raw JSON. If cache miss or low confidence, fall through to direct read.

**P3 — Prime early, query later.** Tier 1 primes the cache with task context so Tier 2 queries are cache hits, not cold searches.

**P4 — Measure everything.** Every CPS-enhanced session logs token savings via `cps_status` so Phase 5 can produce hard numbers.

---

## 3. Prerequisites

CPS must be initialized on the engagement workspace (`cps-init` skill, creates `.cps/` folder). The MCP server must be registered in `.mcp.json`. If either is missing, CPS integration is skipped silently per P1.

### Detection Check (runs once per session)

```
IF .cps/ directory exists AND .mcp.json references cps_server:
  SET cps_available = true
  Call cps_status(detail="summary")
  IF stale_files > 0 OR coverage_pct < 80:
    Call cps_ingest() + cps_graph_build()  // auto-refresh
ELSE:
  SET cps_available = false
  // proceed with standard scan — no warning, no prompt
```

This check runs **before Tier 1**. It is a Step 0 inserted into the startup protocol.

---

## 4. Integration by Tier

### 4.1 Tier 1 — Augment (don't replace)

Tier 1 reads are small structured JSON files (engagement_config, staffing, own folder state, flag counts). These are cheap and CPS doesn't improve them — direct reads stay.

**New step after Tier 1 reads (only if `cps_available = true`):**

```
Call cps_prime(
  task_description = <current task context from last_session.json or consultant intent>,
  include_graph = true,
  limit = 8
)
```

This pre-loads the semantic cache with chunks relevant to the current work context. The prime call itself costs ~200–400 tokens but saves 2,000–5,000 tokens downstream by converting Tier 2 file reads into cache hits.

**If `last_session.json` is absent** (first session), use a generic prime: `"EM startup: open flags, pending handoffs, RIDAC status, schedule variances"`.

### 4.2 Tier 2 — CPS-First, File-Fallback

Tier 2 currently does full-file reads of `flags.json`, `scope_flags.json`, `handoffs.json`, `exceptions.json`, `availability.json`, and `sprint_progress.json` across all persona folders when Tier 1 found pending items.

**CPS-enhanced Tier 2 protocol:**

For each file that Tier 1 flagged as having pending items:

```
1. Call cps_search(
     query = "open [item_type] from [persona]",
     source_filter = "[persona]/[file].json",
     limit = 5
   )

2. Evaluate top result score:
   - score >= 0.35  → USE CPS results, skip file read
   - score 0.25-0.35 → USE CPS results + flag partial confidence
   - score < 0.25   → FALLBACK to direct file read (standard Tier 2)

3. If CPS results used:
   - Extract structured data from chunk text
   - If chunk references need full context, call cps_retrieve(chunk_id)
   - Continue to skill invocation (process-flags, etc.) as normal
```

**Why this works:** CPS chunks JSON files by logical entry (each flag, each handoff). A search for "open flags from ARC" returns the specific open entries, not the entire file. The chunker preserves JSON structure within each chunk.

**What doesn't change:** Skill invocations (process-flags, process-scope-flags) still run identically — they receive the same data, just sourced from cache instead of raw file.

### 4.3 Tier 3 — No Change

Gmail, Slack, SharePoint, and deep RIDAC reads are on-demand MCP calls. CPS doesn't touch external sources. No integration needed.

---

## 5. Token Savings Model

### Baseline: Standard EM Startup (no CPS)

| Step | Tokens (est.) |
|------|---------------|
| Tier 1: 4 config reads | ~800 |
| Tier 2: 4-6 full JSON reads | ~3,000–6,000 |
| Tier 2: skill invocations | ~1,500 |
| ES integration (if connected) | ~1,000 |
| **Total** | **~6,300–9,300** |

### CPS-Enhanced EM Startup

| Step | Tokens (est.) |
|------|---------------|
| Step 0: cps_status + optional refresh | ~100–300 |
| Tier 1: 4 config reads (unchanged) | ~800 |
| Tier 1: cps_prime | ~200–400 |
| Tier 2: cps_search (cache hits) | ~600–1,200 |
| Tier 2: skill invocations (unchanged) | ~1,500 |
| ES integration (unchanged) | ~1,000 |
| **Total** | **~4,200–5,200** |

**Projected savings: 2,000–4,000 tokens per startup (~30–45%).**

The savings compound across sessions. After 3–4 sessions on the same engagement, the cache is warm and Tier 2 hits approach 100% cache rate.

### Measurement

After startup completes, call `cps_status(detail="summary")` and extract:
- `cache.hits` / `cache.misses` — cache hit rate
- `cache.token_savings` — cumulative tokens saved
- `coverage_pct` — index freshness

Include these in the context brief output line: "CPS: [hit_rate]% cache, [savings] tokens saved this session."

---

## 6. EM CLAUDE.md Changes

### 6.1 New Section: CPS Integration (insert after Enterprise Search Integration, before Behavioral Rules)

Add a `### CPS Integration` subsection within the Startup Scan section (after Enterprise Search, before Degraded Mode).

### 6.2 Startup Scan Modifications

**Step 0 (new):** CPS availability check + auto-refresh.

**Tier 1 addition:** `cps_prime` call after config reads.

**Tier 2 modification:** CPS-first query pattern with file-fallback.

**Degraded Mode addition:** "CPS not initialized → skip all CPS steps silently. Note 'CPS unavailable' in context brief. Does not block any scan tier."

### 6.3 Haiku Gateway Addition

Add CPS operations to the Haiku delegation tiers:
- **Tier 1 (mechanical):** `cps_ingest`, `cps_graph_build` (auto-refresh)
- **Tier 3 (bounded search):** `cps_search` queries during Tier 2 scan, `cps_status` checks

---

## 7. Generalization Path (Post-EM Proving Ground)

After EM integration is validated and token savings measured:

1. **ARC:** Tier 2 scans HLD, decision_risk_log, cross-persona handoffs. Same CPS-first pattern. Prime query: "ARC startup: architecture decisions, technical blockers, design review requests."

2. **BPC:** Tier 2 scans RTM gaps, sprint backlog, handoffs. Prime query: "BPC startup: process design feedback, UAT readiness, scope changes."

3. **TC:** Tier 2 scans ARC flags (design changes), handoffs, defects. Prime query: "TC startup: design changes affecting build, pending handoffs, open defects."

Each persona gets the same three modifications: Step 0 detection, Tier 1 prime, Tier 2 CPS-first queries. The only difference is the prime query text and source_filter targets.

---

## 8. Config Requirements

CPS config (`cps_config.json`) needs these settings for startup integration:

```json
{
  "auto_refresh_on_startup": true,
  "source_paths": [
    "Documentation/md/*.md",
    "Reference/*.md",
    "Reference/**/*.md",
    "SNP-*/*/flags.json",
    "SNP-*/*/scope_flags.json",
    "SNP-*/*/handoffs.json",
    "SNP-*/*/exceptions.json",
    "SNP-*/*/availability.json",
    "SNP-*/*/sprint_progress.json"
  ],
  "cache": {
    "similarity_threshold": 0.05,
    "max_age_hours": 24
  }
}
```

**Key addition:** JSON files from engagement workspace folders are now indexed alongside documentation. The chunker must handle JSON array entries as individual chunks (one flag = one chunk, one handoff = one chunk).

---

## 9. Phase 5.1 Enhancements (Implemented 2026-04-07)

Three enhancements addressing the original open questions:

### 9.1 JSON Array Chunking (resolves OQ#1)

New `chunk_json()` function in `cps_chunker.py` and universal `chunk_file()` dispatcher. JSON files are now chunked by structure instead of treated as monolithic text:

- **Top-level arrays:** One chunk per array entry. Entry labels extracted from common identifier fields (`title`, `name`, `id`, `label`, `key`, `slug`).
- **Top-level objects:** Meta keys (`meta`, `_meta`, `metadata`) extracted as chunk frontmatter. One chunk per remaining top-level key. Array-valued keys are sub-chunked per entry.
- **Size constraints:** Same MIN_TOKENS/MAX_TOKENS rules as markdown. Oversized entries split at line boundaries. Undersized entries merged with successor.
- **Ingest routing:** Both `ingest()` and `ingest_files()` now call `chunk_file()` which dispatches by extension (`.json` to `chunk_json`, all else to `chunk_markdown`).

### 9.2 Stale Chunk Purge (resolves OQ#2)

New `purge_stale()` method on `IngestPipeline` and `cps_purge` MCP tool:

- **Missing file detection:** Iterates every manifest entry and checks whether the source file still exists on disk. Removes chunks for deleted files.
- **Age-based purge:** Optional `max_age_days` parameter. Entries whose `last_ingest` timestamp exceeds the threshold are purged regardless of disk state.
- **Cache invalidation:** Semantic cache is cleared after any purge operation.
- **Multi-engagement isolation:** When a consultant switches engagement folders, stale chunks from the previous engagement's paths will fail the disk-existence check and get purged on the next `cps_purge` call.

### 9.3 Prime Query Personalization (resolves OQ#3)

Enhanced `cps_prime` tool with two new parameters:

- **`persona` (ARC|BPC|TC|EM):** Applies a +0.15 score boost to chunks from files matching the persona's scan allowlist. Results are re-sorted after boosting. Allowlists are hardcoded in `PERSONA_ALLOWLISTS` on the server class and match the CLAUDE.md startup scan patterns.
- **`last_session_deltas` (string):** Delta summary from `last_session.json` is appended to the task description before embedding (truncated to 300 chars). This biases the vector search toward chunks related to recent changes without requiring a separate search pass. The delta is folded into the query text, not stored.

Decision: Personalized primes are opt-in (both params optional). The read dependency on `last_session.json` stays in the CP's startup scan, not in CPS itself - CPS receives the delta as a pre-extracted string.

---

## 10. Remaining Open Questions

All three original open questions resolved in Phase 7 (2026-04-07). See Section 11 for designs.

---

## 11. Phase 7 — Open Question Resolutions (Designed 2026-04-07)

### 11.1 Multi-Engagement Cache Isolation (resolves OQ#1) — IMPLEMENTED

**Problem:** `search_cache` table has no engagement context. Switching projects contaminates query results with stale entries from the previous engagement.

**Design:**

- Add `engagement_id TEXT` column to the `search_cache` SQLite table
- Derive engagement ID from workspace folder name (e.g. `SNP-1042`) — same value used in `engagement_config.json`
- `_tool_prime` and `_tool_search` pass engagement ID as a mandatory filter on cache lookups — cache hits only match when `engagement_id = active_engagement`
- Add `purge_engagement` mode to `purge_stale`: clears all cache + chunk entries for a given engagement ID without touching other engagements
- On `cp-setup swap` (engagement switch), persona CLAUDE.md instructs `cps_purge --engagement <old_id>` before the new startup scan
- Existing entries with NULL `engagement_id` are treated as stale (cache miss on lookup, eventually purged)
- No schema migration needed — SQLite `ALTER TABLE ADD COLUMN` handles it; NULL defaults are safe

**Scope:** `cps_server.py` (cache table schema, lookup query, purge method), persona CLAUDE.md swap instructions.

### 11.2 Persona Allowlist Dynamic Loading (resolves OQ#2) — IMPLEMENTED

**Problem:** Hardcoded `PERSONA_ALLOWLISTS` dict in `cps_server.py` will drift from CLAUDE.md startup scan definitions as personas evolve.

**Design:**

- Add `persona_allowlists` section to `engagement_config.json` (already written by `cp-setup`):
  ```json
  "persona_allowlists": {
    "ARC": ["Architect/", "decision_risk_log", "hld", "as-built", "runbook", "staffing.json", "activity_log.json", "project_index.json"],
    "BPC": ["BPC/", "rtm", "process", "uat", "workshop", "staffing.json", "activity_log.json", "project_index.json"],
    "TC": ["TC/", "defect", "story", "unit-test", "update-set", "smoke-test", "staffing.json"],
    "EM": ["EM/", "ridac", "schedule", "status", "flags.json", "scope_flags.json", "handoffs.json", "staffing.json", "activity_log.json", "project_index.json", "engagement_config"]
  }
  ```
- On CPS init, `cps_server.py` reads `engagement_config.json → persona_allowlists` instead of using the hardcoded dict
- If the field is missing (backwards compat), fall back to the current hardcoded `PERSONA_ALLOWLISTS` defaults
- `cp-setup` becomes the single source of truth for both CLAUDE.md scan paths and CPS filter rules — one place to update

**Scope:** `cps_server.py` (init path, remove hardcoded dict), `engagement_config.json` schema, `cp-setup` skill (write allowlists on init/refresh), Schema Definitions (add field).

### 11.3 JSON Chunker Structural Repair (resolves OQ#3) — IMPLEMENTED

**Problem:** Deeply nested JSON (3+ levels) is serialized and split at line boundaries when oversized, which can break JSON structure in chunk text.

**Assessment:** Embedding quality is not affected — embedding models encode semantic meaning, not syntactic structure. A chunk containing partial JSON still embeds meaningfully. However, when chunks are returned to personas for context, broken JSON is confusing and may cause misinterpretation.

**Design:**

- In `_split_json_text` (cps_chunker.py), after splitting at line boundaries, run a bracket-balance check on each resulting chunk
- If unbalanced: append closing tokens (`]`, `}`) to make the chunk parseable, and prepend `// [truncated from parent structure]` as a context hint
- Add `"truncated": true` flag to chunk metadata so the query layer can surface a warning to the persona
- Cost: single-pass string scan for bracket balance per split chunk — negligible overhead

**Scope:** `cps_chunker.py` (`_split_json_text` function, chunk metadata), `cps_server.py` (query result rendering — optional truncation warning).
