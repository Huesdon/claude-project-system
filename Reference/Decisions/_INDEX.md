# Index

Entries added by `cps-capture` as patterns, decisions, and lessons accumulate.

- [Prefer runtime self-heal over installer pre-fetch for model downloads](2026-04-09-self-heal-over-installer-prefetch.md) — Fix embedder model-missing errors in the runtime, not the installer, so every caller inherits the fix.
- [Drop MCP auto-start for on-demand CLI subprocess](2026-04-09-drop-mcp-autostart-for-cli-subprocess.md) — Replace brittle .mcp.json auto-launch with subprocess calls to cps_server.py CLI mode.
- [Gate Conditional CLAUDE.md Sections Behind Reference Doc Pointers](2026-04-09-gate-conditional-claudemd-sections.md) — Move runtime-conditional sections to Reference/ and replace with a gate-check stub to avoid per-session token waste.
