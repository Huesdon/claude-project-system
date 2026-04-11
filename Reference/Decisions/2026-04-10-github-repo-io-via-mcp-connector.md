# GitHub Repo I/O via MCP Connector (Retire gh_pull.py + gitpush.bat)

**Date:** 2026-04-10
**Status:** Accepted

## Context
CPS dev sessions previously had no direct GitHub API access from within Cowork. Two workarounds existed: `Runtime/gh_pull.py` (raw-URL fetch + hash-diff for truncation recovery) and `Runtime/gitpush.bat` (robocopy sync + git push from a detached-clone at `H:\Github\cowork-project-system`). The .bat approach was also broken — it shipped a `SESSION_COMMIT_MESSAGE_PLACEHOLDER` that was never substituted. On 2026-04-10 Shane connected the GitHub MCP connector, giving Claude direct API access in-session.

## Decision
Use `mcp__github__get_file_contents`, `mcp__github__create_or_update_file`, `mcp__github__push_files`, and `mcp__github__list_commits` for all GitHub repo I/O during CPS dev sessions. Retire `gh_pull.py` and `gitpush.bat`.

## Alternatives rejected
- **Keep gitpush.bat as primary** — broken (placeholder never substituted), requires manual StreamDeck press, adds latency between edit and push, no error feedback in session.
- **Keep gh_pull.py as CLI fallback** — redundant now that `get_file_contents` provides the same hash-diff capability with zero subprocess overhead. Risk of further drift as a second code path.
- **Use `gh` CLI via Bash** — sandbox doesn't reliably have `gh` auth; still a subprocess; adds complexity with no benefit over direct MCP calls.

## Rationale
MCP tools are synchronous, authenticated, and return structured JSON — no subprocess, no raw URL fetch, no robocopy. Claude can now read, write, and push in-session as part of the normal edit flow, eliminating the entire "remember to push before close" burden. Downstream skills (`cps-init`, `cps-patcher`) still use raw HTTP fetches because they run in end-user sessions without the connector — that split is intentional and unchanged.

## Consequences
- **Easier:** pushing scaffold edits, patch catalog entries, and CLAUDE.md updates — all become in-session steps Claude handles automatically.
- **Harder:** nothing meaningful. MCP connector must be connected at session start — if it drops, falls back to manual push from `H:\Github\cowork-project-system` (detached clone still exists).
- **Newly required:** CLAUDE.md §0 "GitHub repo I/O" rule governs all future dev sessions. Mount-corruption rule still applies — no local `git init` inside Cowork mount.
