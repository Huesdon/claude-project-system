# CPS Session Startup Protocol

> **Rev 2 (2026-04-09):** Rewritten for CLI-on-demand model. MCP server wiring removed in cps-setup rev 4. No startup probe needed.
> **Rev 1:** MCP-based — `cps_status` probe + `needs_refresh` auto-ingest. Archived below.

---

## Current Protocol (CLI-on-demand)

CPS requires no startup action. Tools are invoked on demand via skills:

| Task | How |
|------|-----|
| Search knowledge base | `cps-query` skill |
| Refresh index after changes | `cps-refresh` skill |
| Capture a pattern/decision/lesson | `cps-capture` skill |

**No `.mcp.json` check. No `cps_status` probe. No auto-ingest.**

CPS is available in any session where `.cps/cps_server.py` exists in the project root.

### Manual CLI (no skill needed)

```bash
# Search
python .cps/cps_server.py search --query "your question" --top_k 5

# Ingest
python .cps/cps_server.py ingest

# Status
python .cps/cps_server.py status
```

All commands emit clean JSON on stdout. Logs go to stderr and do not contaminate the JSON response.

---

## Archived: Rev 1 MCP Protocol

> Preserved for reference only. Do not apply — the MCP server is no longer wired.

**Steps (old):**
1. Check `.mcp.json` for `cps` server entry. If absent, skip entirely.
2. Run `cps_status`. If `needs_refresh: true`, run `cps_ingest` before starting work.
3. If ingest touched >10 files, call `cps_graph_build`.

**Removed items:**
- `cps_prime` warmup — speculative work, removed in rev 11
- `auto_refresh_on_startup` config flag — replaced by conditional `needs_refresh` logic, then dropped entirely in rev 14 (CLI model)
- `.mcp.json` auto-startup template — removed from cps-setup in Step 11 drop (task `t2-cps-setup-drop-step11`)
