<#
.SYNOPSIS
    CPS scaffold — standalone PowerShell port of the cps-init skill.

.DESCRIPTION
    Creates the Claude Project System (CPS) Core or Full folder structure on
    the local Windows filesystem. Bypasses Cowork sandbox write issues entirely.
    Idempotent — safe to re-run; existing non-empty files are preserved.

    Mirrors the cps-init skill logic:
      1. Directory scaffold (Reference/, Documentation/md/, Input/, Output/)
      2. _INDEX.md stubs with CREATED / REPAIRED / SKIPPED outcome classification
      3. Canonical reference docs (CPS_Task_Module.md, CPS_TOC_Rule.md,
         CPS_Capture_Taxonomy.md) with rev-marker upgrade logic
      4. CLAUDE.md section injection via BEGIN/END delimited blocks
         (cleaner than the single-marker scheme in the skill — safer replace).

.PARAMETER Path
    Target project directory. Defaults to the folder the script itself lives in
    ($PSScriptRoot). Drop the script into any project folder and run it — no
    arguments required. Double-click via the companion cps-scaffold.cmd.

.PARAMETER Profile
    'core' or 'full'. If omitted, prompts interactively.

.PARAMETER Force
    Overwrite existing canonical docs regardless of rev marker.

.EXAMPLE
    .\cps-scaffold.ps1
    .\cps-scaffold.ps1 -Path "C:\Projects\MyApp" -Profile full
    .\cps-scaffold.ps1 -Profile core -Force
#>

[CmdletBinding()]
param(
    [string]$Path = '',
    [ValidateSet('core','full','')]
    [string]$ProfileName = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

# Default target = the folder this script lives in, so a user can drop the
# script into any project and run it in place. Fallback to the current working
# directory if $PSScriptRoot is unavailable (dot-sourced edge case).
if (-not $Path) {
    if ($PSScriptRoot) {
        $Path = $PSScriptRoot
    } else {
        $Path = (Get-Location).Path
    }
}

# --------------------------------------------------------------------------
# Embedded template revs (match cps-init templates/ as of 2026-04-09)
# --------------------------------------------------------------------------
$TaskModuleRev    = 2
$TocRuleRev       = 1
$CaptureRev       = 2
$CoreSectionRev   = 3
$FullSectionRev   = 1

# --------------------------------------------------------------------------
# Embedded templates (single-quoted here-strings = verbatim, no interpolation)
# --------------------------------------------------------------------------

$IndexPatterns = @'
# Patterns Index

Entries added by `cps-capture` as reusable techniques and design approaches accumulate.
'@

$IndexDecisions = @'
# Decisions Index

Entries added by `cps-capture` as design decisions (with context and rationale) accumulate.
'@

$IndexLessons = @'
# Lessons Index

Entries added by `cps-capture` as gotchas and hard-won lessons accumulate.
'@

$IndexIdeas = @'
# Ideas Index

Nascent ideas, exploration candidates, and "what if" items. Capture early, promote when ready.
Use `cps-capture` with trigger "add idea". Promote to Roadmap with "promote [title] to roadmap".

<!-- entries below -->
'@

$IndexRoadmap = @'
# Roadmap Index

Committed intentions, not yet active tasks. Each item has a goal, rationale, and horizon (Now/Next/Later).
Use `cps-capture` with trigger "add to roadmap". Promote to tasks with "promote [title] to tasks".

<!-- entries below -->
'@

$TaskModule = @'
<!-- rev: 2 -->
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

Before ending any session, call `task COMPLETE` on every item finished. Completed tasks are removed from `tasks.json` and appended as a single line to `Reference/Claude/tasks_completed.log` (format: `YYYY-MM-DD | task-id | title`). Do not leave checkmark stubs or strikethrough entries in `tasks.json` — they burn tokens on every future RECOMMEND pass. The log preserves history without bloating the active backlog.

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
'@

$TocRule = @'
<!-- rev: 1 -->
# CPS TOC Maintenance Rule (MANDATORY)

> Externalized from CLAUDE.md §11 on 2026-04-08 to reduce per-session token cost. CLAUDE.md retains a one-line summary pointing at this file.

Every `Reference/` or `Documentation/md/` file that exceeds **200 lines** must have a companion `_TOC.md` file. The TOC lists every `##` and `###` heading with its line number in a two-column markdown table (`Line | Section`). This enables targeted `offset`/`limit` reads instead of loading full documents and is the mechanism that lets the §7 read hierarchy actually work.

## When to Create a TOC

- Delegation: Use Haiku (Tier 1) to generate TOC tables from finished files.
- Any new `Reference/` or `Documentation/md/` file that is written above 200 lines, or any existing file that grows past 200 lines during edits.
- Immediately — not deferred to a cleanup pass.
- Created in the same session as the doc itself; do not close a session with an over-threshold doc that lacks a TOC.

## TOC File Naming and Location

- Same directory as the source file.
- Name: `[SourceFilename]_TOC.md` (e.g. `CPS_Integration_Spec_TOC.md`).
- Format: a two-column markdown table with header `| Line | Section |`, one row per `##` or `###` heading, line numbers absolute.

## After Adding or Removing a TOC

1. Update the corresponding row in the CLAUDE.md §7 doc table (Lines column + TOC column).
2. Update the TOC count line directly under the table ("TOC count: N docs").
3. Run `cps-refresh` so the new TOC is indexed and discoverable to query callers.

## Authoritative Registry

The CLAUDE.md §7 doc table is the single source of truth for TOC coverage. If a doc is over threshold and the TOC column is empty, the project is out of compliance and should be fixed before any new doc work begins. Do not rely on filesystem scans — the table is the canonical answer.

## Exemption — CLAUDE.md Files

CLAUDE.md is always fully loaded at session start, so a TOC produces no token savings for the file itself. CLAUDE.md files are exempt from the 200-line TOC threshold. Apply normal session-hygiene pressure instead: keep CLAUDE.md tight by folding stale phase history, retiring dead sections, and pushing rationale into Reference/*.md files.
'@

$CaptureTaxonomy = @'
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
- **Idea → Roadmap:** "promote [title] to roadmap" — creates a Roadmap entry referencing the source idea; updates idea Status to "Promoted".
- **Roadmap → Tasks:** "promote [title] to tasks" — spawns task entries in tasks.json via the `task` skill; updates roadmap Status to "Promoted".

**Claude-initiated capture (self-trigger).** Claude proactively flags a candidate mid-conversation when all four of these are true:
1. The knowledge is reusable across future sessions or projects
2. A future Claude would miss it if not captured
3. The *why* can be stated in one sentence
4. There is a clear bucket fit (Pattern / Decision / Lesson / Idea / Roadmap)

For Ideas, the self-trigger bar is lower: flag if something surfaces that seems worth exploring but isn't ready to be a task.

When Claude flags a candidate, it pauses, states it in one line, and asks "worth capturing?" before writing. Max one self-trigger prompt per ~5 exchanges to avoid interview mode.

**Capture flow:** User or Claude flags → Claude drafts content → Haiku (Tier 4) writes files + updates _INDEX.md → `cps-refresh` auto-runs → indexed.

**After capture:** If significant enough that future sessions must not miss it, suggest adding a pointer to this CLAUDE.md — but do not edit without explicit user approval.
'@

$CoreSectionBlock = @'
<!-- cps-core BEGIN rev: 3 -->
<!-- Managed by cps-scaffold.ps1 — do not edit between BEGIN/END markers; re-run the script to update. -->

## Delegation

Tier 1–4 mechanical tasks (file writes, mutations, formatting, transforms) delegate to Haiku. Sonnet handles architecture and decisions. See user preferences for the full routing heuristic.

---

## Session Startup

On session open: surface top 1–3 active tasks (§9 RECOMMEND) before any other work. Load memory if available. Do not scope-clarify vague openers when a task backlog exists.

---

## Document Access Hierarchy

1. This CLAUDE.md (always loaded)
2. `_TOC.md` companions (for any Reference/ or Documentation/md/ doc >200 lines)
3. Targeted section reads with `offset`/`limit`
4. Full doc reads — last resort only

---

## Documentation

- `Reference/` — canonical design docs, patterns, decisions, lessons
- `Documentation/md/` — user-facing markdown docs

---

## Input / Output Folders

- `Input/` — drop source materials here for Claude to pick up and analyze. Markdown files in `Input/` are indexed by CPS (Full profile) via `Input/**/*.md` in `source_paths`.
- `Output/` — **default drop zone for all Claude-generated deliverables** (reports, exports, presentations, one-off artifacts) that don't belong in `Documentation/` or `Reference/`. Claude writes deliverables here unless directed elsewhere.

---

## 9. Task Module — Trigger Summary

Session-start RECOMMEND, tier-based backlog, single source of truth in `Reference/Claude/tasks.json`.
Full spec: `Reference/Claude/CPS_Task_Module.md`. Owned by the `task` skill.

---

## 11. TOC Maintenance Rule

Any `Reference/` or `Documentation/md/` file over 200 lines requires a companion `[SourceFilename]_TOC.md` in the same directory.
Full spec: `Reference/Claude/CPS_TOC_Rule.md`.

---

## 12. Knowledge Capture — Taxonomy

Five buckets under `Reference/`: Patterns, Decisions, Lessons, Ideas (low-friction, promote when ready), Roadmap (committed intentions with Now/Next/Later horizon). Self-trigger gate requires all four capture criteria (Ideas have a lower bar). Promotion flow: Idea→Roadmap→Tasks.
Full spec: `Reference/Claude/CPS_Capture_Taxonomy.md`.
Trigger phrases: "add idea", "add to roadmap", "promote [title] to roadmap", "promote [title] to tasks".

<!-- cps-core END -->
'@

$FullSectionBlock = @'
<!-- cps-full BEGIN rev: 1 -->
<!-- Managed by cps-scaffold.ps1 — do not edit between BEGIN/END markers; re-run the script to update. -->

## CPS Server Protocol

Semantic search via `.cps/`. On demand — no session startup probe required.

- **Query:** invoke `cps-query` skill (or `python .cps/cps_server.py search --query "..."`)
- **Refresh:** invoke `cps-refresh` after doc/code changes
- **Capture:** invoke `cps-capture` for knowledge entries

Available whenever `.cps/cps_server.py` exists in the project root.

<!-- cps-full END -->
'@

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

$Script:Outcomes = @()

function Add-Outcome {
    param([string]$Action, [string]$Target)
    $Script:Outcomes += [PSCustomObject]@{ Action = $Action; Target = $Target }
}

function Ensure-Directory {
    param([string]$Dir)
    if (Test-Path -LiteralPath $Dir) {
        Add-Outcome 'SKIPPED-dir' $Dir
        return $false
    }
    New-Item -ItemType Directory -Path $Dir -Force | Out-Null
    Add-Outcome 'CREATED-dir' $Dir
    return $true
}

function Write-StubFile {
    param(
        [string]$FilePath,
        [string]$Content,
        [bool]$ParentWasJustCreated
    )
    if (Test-Path -LiteralPath $FilePath) {
        $existing = Get-Content -LiteralPath $FilePath -Raw -ErrorAction SilentlyContinue
        if ($existing -and $existing.Trim().Length -gt 0) {
            Add-Outcome 'SKIPPED' $FilePath
            return
        }
        Set-Content -LiteralPath $FilePath -Value $Content -Encoding UTF8 -NoNewline
        Add-Outcome 'REPAIRED' $FilePath
        return
    }
    Set-Content -LiteralPath $FilePath -Value $Content -Encoding UTF8 -NoNewline
    if ($ParentWasJustCreated) {
        Add-Outcome 'CREATED' $FilePath
    } else {
        Add-Outcome 'REPAIRED' $FilePath
    }
}

function Get-EmbeddedRev {
    param([string]$Content)
    if ($Content -match '<!--\s*rev:\s*(\d+)\s*-->') {
        return [int]$Matches[1]
    }
    return 0
}

function Write-CanonicalDoc {
    param(
        [string]$FilePath,
        [string]$Content,
        [int]$EmbeddedRev
    )
    if (Test-Path -LiteralPath $FilePath) {
        if ($Force) {
            Set-Content -LiteralPath $FilePath -Value $Content -Encoding UTF8 -NoNewline
            Add-Outcome 'FORCED' $FilePath
            return
        }
        $existing = Get-Content -LiteralPath $FilePath -Raw -ErrorAction SilentlyContinue
        $existingRev = Get-EmbeddedRev $existing
        if ($existingRev -ge $EmbeddedRev) {
            Add-Outcome 'SKIPPED' $FilePath
            return
        }
        Set-Content -LiteralPath $FilePath -Value $Content -Encoding UTF8 -NoNewline
        Add-Outcome "UPGRADED rev $existingRev->$EmbeddedRev" $FilePath
        return
    }
    Set-Content -LiteralPath $FilePath -Value $Content -Encoding UTF8 -NoNewline
    Add-Outcome 'CREATED' $FilePath
}

function Update-ClaudeMdBlock {
    param(
        [string]$FilePath,
        [string]$Tag,      # 'cps-core' or 'cps-full'
        [string]$Block,
        [int]$EmbeddedRev
    )
    if (-not (Test-Path -LiteralPath $FilePath)) {
        $header = "# CLAUDE.md`n"
        Set-Content -LiteralPath $FilePath -Value ($header + "`n" + $Block + "`n") -Encoding UTF8 -NoNewline
        Add-Outcome "CREATED w/ $Tag" $FilePath
        return
    }

    $content = Get-Content -LiteralPath $FilePath -Raw
    if (-not $content) { $content = '' }
    $beginPattern = [regex]::Escape("<!-- $Tag BEGIN rev:")

    if ($content -match "$beginPattern\s*(\d+)\s*-->") {
        $existingRev = [int]$Matches[1]
        if ((-not $Force) -and ($existingRev -ge $EmbeddedRev)) {
            Add-Outcome "SKIPPED $Tag block" $FilePath
            return
        }
        $escTag = [regex]::Escape($Tag)
        $pattern = "(?s)<!--\s*${escTag}\s*BEGIN\s*rev:\s*\d+\s*-->.*?<!--\s*${escTag}\s*END\s*-->"
        $match = [regex]::Match($content, $pattern)
        if ($match.Success) {
            $newContent = $content.Substring(0, $match.Index) + $Block + $content.Substring($match.Index + $match.Length)
            Set-Content -LiteralPath $FilePath -Value $newContent -Encoding UTF8 -NoNewline
            Add-Outcome "UPGRADED $Tag rev $existingRev->$EmbeddedRev" $FilePath
            return
        }
    }

    # Append at end
    $needsNewline = -not $content.EndsWith("`n")
    $appendage = ($(if ($needsNewline) { "`n`n" } else { "`n" })) + $Block + "`n"
    Add-Content -LiteralPath $FilePath -Value $appendage -Encoding UTF8
    Add-Outcome "APPENDED $Tag block" $FilePath
}

# --------------------------------------------------------------------------
# Profile menu
# --------------------------------------------------------------------------

if (-not $ProfileName) {
    Write-Host ""
    Write-Host "CPS Scaffold" -ForegroundColor Cyan
    Write-Host "============" -ForegroundColor Cyan
    Write-Host "Target: $Path"
    Write-Host ""
    Write-Host "Select profile:"
    Write-Host "  1) Core   - scaffold + three pillars, no Python runtime"
    Write-Host "  2) Full   - Core + CPS Server Protocol section in CLAUDE.md"
    Write-Host ""
    $choice = Read-Host "Choose [1-2]"
    switch ($choice.Trim()) {
        '1' { $ProfileName = 'core' }
        '2' { $ProfileName = 'full' }
        default {
            Write-Host "Invalid choice. Aborting." -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "Scaffolding CPS ($ProfileName) into: $Path" -ForegroundColor Green
Write-Host ""

if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}
$Path = (Resolve-Path -LiteralPath $Path).Path

# --------------------------------------------------------------------------
# Step 1: directories
# --------------------------------------------------------------------------

$dirSpecs = @(
    'Reference',
    'Reference\Claude',
    'Reference\Patterns',
    'Reference\Decisions',
    'Reference\Lessons',
    'Reference\Ideas',
    'Reference\Roadmap',
    'Documentation',
    'Documentation\md',
    'Input',
    'Output'
)

$dirCreated = @{}
foreach ($rel in $dirSpecs) {
    $full = Join-Path $Path $rel
    $dirCreated[$rel] = Ensure-Directory $full
}

# --------------------------------------------------------------------------
# Step 2: _INDEX.md stubs
# --------------------------------------------------------------------------

Write-StubFile (Join-Path $Path 'Reference\Patterns\_INDEX.md')  $IndexPatterns  $dirCreated['Reference\Patterns']
Write-StubFile (Join-Path $Path 'Reference\Decisions\_INDEX.md') $IndexDecisions $dirCreated['Reference\Decisions']
Write-StubFile (Join-Path $Path 'Reference\Lessons\_INDEX.md')   $IndexLessons   $dirCreated['Reference\Lessons']
Write-StubFile (Join-Path $Path 'Reference\Ideas\_INDEX.md')     $IndexIdeas     $dirCreated['Reference\Ideas']
Write-StubFile (Join-Path $Path 'Reference\Roadmap\_INDEX.md')   $IndexRoadmap   $dirCreated['Reference\Roadmap']

# --------------------------------------------------------------------------
# Step 3: canonical reference docs (rev-aware)
# --------------------------------------------------------------------------

Write-CanonicalDoc (Join-Path $Path 'Reference\Claude\CPS_Task_Module.md')      $TaskModule      $TaskModuleRev
Write-CanonicalDoc (Join-Path $Path 'Reference\Claude\CPS_TOC_Rule.md')         $TocRule         $TocRuleRev
Write-CanonicalDoc (Join-Path $Path 'Reference\Claude\CPS_Capture_Taxonomy.md') $CaptureTaxonomy $CaptureRev

# --------------------------------------------------------------------------
# Step 4: CLAUDE.md sections
# --------------------------------------------------------------------------

$claudeMd = Join-Path $Path 'CLAUDE.md'
Update-ClaudeMdBlock $claudeMd 'cps-core' $CoreSectionBlock $CoreSectionRev

if ($ProfileName -eq 'full') {
    Update-ClaudeMdBlock $claudeMd 'cps-full' $FullSectionBlock $FullSectionRev
}

# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

Write-Host ""
Write-Host "Outcomes" -ForegroundColor Cyan
Write-Host "--------"
$Script:Outcomes | Sort-Object Action, Target | Format-Table -AutoSize | Out-String | Write-Host

$createdCount  = ($Script:Outcomes | Where-Object { $_.Action -like 'CREATED*' }).Count
$repairedCount = ($Script:Outcomes | Where-Object { $_.Action -like 'REPAIRED*' }).Count
$upgradedCount = ($Script:Outcomes | Where-Object { $_.Action -like 'UPGRADED*' -or $_.Action -like 'APPENDED*' -or $_.Action -like 'FORCED*' }).Count
$skippedCount  = ($Script:Outcomes | Where-Object { $_.Action -like 'SKIPPED*' }).Count

Write-Host ("Summary: {0} created, {1} repaired, {2} upgraded/appended, {3} skipped." -f `
    $createdCount, $repairedCount, $upgradedCount, $skippedCount) -ForegroundColor Green
Write-Host ""
Write-Host "Done. Profile: $ProfileName" -ForegroundColor Green

if ($ProfileName -eq 'full') {
    Write-Host ""
    Write-Host "Next step: run cps-installer (or cps-setup full) to deploy the Python runtime and .cps/ database." -ForegroundColor Yellow
}
