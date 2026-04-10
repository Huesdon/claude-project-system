# CPS Deployment Checklist (New Project)

> Externalized from CLAUDE.md §10 on 2026-04-08 to reduce per-session token cost. Consult this file only when deploying CPS to a new Cowork project.
> Last updated: 2026-04-10 — updated to reflect cps-setup as the canonical installer.

`cps-setup` is the **canonical and only** install path. It is menu-driven (Core or Full), auto-detects existing Core scaffolds for graceful upgrade, and delegates scaffold writes to `cps-init` (which runs `cps_scaffold.py` via Python). `cps-installer` and `cps-platform` are deprecated — do not reference them in new project docs.

When deploying CPS to a new Cowork project:

- [ ] Confirm `cps-setup.skill`, `cps-init.skill`, `task.skill`, and `cps-capture.skill` are installed globally (`~/.claude/skills/`) before running — cps-setup halts with instructions if any pillar skill is missing
- [ ] Open a session in the target project and say "install cps"
- [ ] Choose profile: **Core** (scaffold + three pillars, no runtime, ≤~100 files) or **Full** (Core + Python runtime + semantic search, ≥~100 files)
- [ ] Confirm cps-init ran successfully (Step 6) and created `Reference/` scaffold + CLAUDE.md §9/§11/§12 pointer sections
- [ ] **Full only:** Confirm `cps_test_suite.py` ran and reported PASS on all infrastructure sections. T2 keyword warnings are acceptable on non-CPS projects.
- [ ] **Full only:** Verify `cps_status` reports chunks > 0 after initial ingest
- [ ] If the target project does not yet have a CLAUDE.md §9 Task Module section, run the `task` skill to install the standard scaffold (cps-setup deliberately does not auto-write §9 — that is the `task` skill's responsibility)
