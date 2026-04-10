# Drop MCP auto-start for on-demand CLI subprocess

**Date:** 2026-04-09
**Status:** Accepted (implementation deferred to fresh session)

## Context

CPS ships as an MCP server that must auto-launch when a Cowork session opens a CPS-enabled project. Auto-launch depends on: Cowork reading `.mcp.json`, resolving the `command` field (`python` vs `python3`), launching from the correct cwd so the relative `.cps/cps_server.py` path resolves, and surfacing any startup failure to the user.

In practice this fails silently on Windows (no `python3` binary by default), on cwd drift, and on any path-resolution mismatch. When it fails, the `cps_*` MCP tools are simply absent from the session and the user cannot query CPS at all. Shane hit this repeatedly, most recently while trying to run `cps-capture` in a freshly-installed MSB project and on session starts in the CPS project itself.

## Decision

Drop MCP auto-start entirely. The `cps-query`, `cps-refresh`, and `cps-capture` skills will shell out to `python .cps/cps_server.py <command> --format=json` on demand via subprocess, bypassing the MCP protocol.

## Alternatives rejected

- **Debug the `.mcp.json` wiring** — fix Windows `python3` → `python`, pin cwd, surface startup errors. Rejected: every downstream change to Cowork's MCP launch semantics re-breaks it. The abstraction isn't earning its keep.
- **Daemon mode + named pipe / unix socket** — first call spawns a background Python that handles subsequent calls. Rejected for now as premature optimization. Cold load is ~1s per query which is invisible at interactive speeds. Add only if rapid-fire querying actually surfaces latency pain.
- **Keep MCP as primary, fall back to CLI on failure** — rejected: two code paths, double the test surface, both must work. Pick one.

## Rationale

- MCP auto-start is a brittle abstraction over what is fundamentally a subprocess call. Calling the subprocess directly removes four failure modes (Cowork launch semantics, PATH resolution, cwd drift, silent errors) at the cost of ~1s embedder cold-load per query.
- `cps_server.py` already has CLI mode — `python cps_server.py search|ingest|status|retrieve` usage lines are in the file. The infrastructure exists; we're just removing a layer.
- On-demand is lazy by default: no startup tax, no warmup, server only runs when a skill actually needs it.
- Dog-fooding the simplest thing that could possibly work. If latency becomes a pain point later, daemon mode is a drop-in upgrade informed by real usage data.

## Consequences

- **Skill rewrites:** `cps-query`, `cps-refresh`, and `cps-capture` all replace `mcp__cps__*` calls with `subprocess.run(["python", ".cps/cps_server.py", ...])`.
- **Installer simplification:** `cps-setup` Step 11 (`.mcp.json` wiring) deleted. One less failure mode in the install path.
- **CLI JSON contract:** `cps_server.py` CLI mode must emit clean JSON on stdout. Verify before the rewrite; patch if not.
- **CLAUDE.md §8 rewrite:** Session Startup Protocol drops the `cps_status` probe, the `needs_refresh` auto-ingest, and any warmup step. CPS server state is no longer tracked at session level.
- **Existing installs:** stale `.mcp.json` `cps` entries stay — harmless, ignored. No migration required.
- **Cold-load accepted:** ~1s ONNX embedder load per query is the new baseline. Revisit only if it actually hurts.
- **Windows install path:** removes the `python3` binary dependency, making CPS install-and-run clean on Windows for the first time.
- **Model cache stays shared:** `~/.cps/models/all-MiniLM-L6-v2/` is still the shared ONNX cache across projects on the same machine — no change there.

## Implementation plan (fresh session)

1. Verify `cps_server.py` CLI mode emits clean JSON on stdout for `search`, `status`, `ingest`. Patch if not.
2. Rewrite `cps-query` SKILL.md to shell out via subprocess. Same for `cps-refresh` and `cps-capture`'s auto-ingest step.
3. Delete `cps-setup` Step 11 and the `.mcp.json` template copy.
4. Rewrite `CLAUDE.md` §8 Session Startup Protocol to drop MCP probes.
5. Bump `cps-setup` and the three skill revs. Rebundle.
6. Test on MSB (the project that exposed the bug) as the validation target.
