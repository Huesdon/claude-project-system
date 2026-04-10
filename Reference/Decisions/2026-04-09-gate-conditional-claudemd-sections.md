# Gate Conditional CLAUDE.md Sections Behind Reference Doc Pointers

**Date:** 2026-04-09
**Status:** Accepted

## Context
CLAUDE.md is fully loaded on every session. Sections that only apply when a runtime condition is true (e.g., a specific MCP server is active) consume tokens unconditionally — even in the majority of sessions where the condition is false. The CPS §8 Session Startup Protocol (~28 lines) was loaded every session despite being relevant only when the `cps` MCP server is running.

## Decision
Move conditional CLAUDE.md sections to `Reference/*.md` and replace them with a 3–5 line stub: a gate check (how to detect the condition) and a pointer to the Reference doc.

## Alternatives rejected
- **Keep inline** — wastes ~400 tokens/session when condition is false; no compensating upside.
- **Comment out** — markdown has no native comment syntax that all parsers suppress; still loads in many contexts.

## Rationale
CLAUDE.md has no conditional loading mechanism — every line costs tokens every session. A gate check + pointer costs ~5 lines; the full content costs 28+. The Reference doc is read only when actually needed, preserving the content without paying the per-session tax.

## Consequences
- Session startup is leaner for sessions where the gated condition is false.
- The Reference doc must be kept in sync with the section it replaced — drift is the main risk.
- Pattern generalizes: any CLAUDE.md section beginning with "only applies when X is running/configured" is a candidate for this treatment.
