# Index

Entries added by `cps-capture` as patterns, decisions, and lessons accumulate.

- [Prefer runtime self-heal over installer pre-fetch for model downloads](2026-04-09-self-heal-over-installer-prefetch.md) — Fix embedder model-missing errors in the runtime, not the installer, so every caller inherits the fix.
- [Drop MCP auto-start for on-demand CLI subprocess](2026-04-09-drop-mcp-autostart-for-cli-subprocess.md) — Replace brittle .mcp.json auto-launch with subprocess calls to cps_server.py CLI mode.
- [Gate Conditional CLAUDE.md Sections Behind Reference Doc Pointers](2026-04-09-gate-conditional-claudemd-sections.md) — Move runtime-conditional sections to Reference/ and replace with a gate-check stub to avoid per-session token waste.
- [Delegate CPS scaffolding to externally-managed CMD+PS1 pair](2026-04-09-scaffold-via-external-cmd-ps1.md) — cps-init becomes a prompt wrapper; `.cmd`/`.ps1` live in Reference/ outside the skill rebundle cycle; Windows-only accepted
- [GitHub Repo I/O via MCP Connector](2026-04-10-github-repo-io-via-mcp-connector.md) — retire gh_pull.py + gitpush.bat; use MCP github tools for all dev-session repo I/O
- [Persistent deps via pip --target .cps/deps + PYTHONPATH](2026-04-08-dep-persistence-pip-target.md) — pip cache is ephemeral; install into bindfs-mounted .cps/deps/ for 14-80× faster cold boot vs rev 9 bootstrap
- [Skills/src/ as canonical skill source tree + committed rebundle helper](2026-04-11-skills-src-as-canonical-source-tree.md) — Skills/src/<name>/ is the persistent edit target; .skill zips are build artifacts; Skills/tools/rebundle.py is the sanctioned build path.
- [CPS is a solo-developer system](2026-04-11-cps-permanently-single-tenant.md) — (scope-corrected 2026-04-11) Solo-dev, one-machine, multi-project. Reject multi-tenant / distribution / cross-machine design premises.
- [Plugin Decoupling — Hoist github MCP, Drop 4 Unused Plugins](2026-04-11-plugin-decoupling.md) — Hoist github MCP to project-local .mcp.json, drop engineering + productivity + product-management + cowork-plugin-management; keep operations (other project) and enterprise-search (no per-project scope).
- [CPS Upgrade Model: Two Entry Points, No Patcher](2026-04-11-cps-upgrade-model-two-entry-points.md) — cps-init for scaffold, cps-setup for runtime/schema. Rev-gated cps_scaffold.py makes re-run cps-init the canonical upgrade path; patcher retired as duplicated scaffolding logic.
