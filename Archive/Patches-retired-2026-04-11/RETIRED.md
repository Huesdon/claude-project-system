# Patches/ retired 2026-04-11

This directory was archived as part of the `cps-patcher` retirement migration (`t1-execute-patcher-retirement`). The patcher skill and its catalog are no longer in use.

**Retirement decision:** `Reference/Decisions/2026-04-11-cps-upgrade-model-two-entry-points.md`
**Retirement rationale (short):** every patch in the catalog (p001–p007) duplicated logic already in `cps_scaffold.py`. The scaffolder is rev-gated and idempotent, so re-running `cps-init` is the canonical scaffold-upgrade operation. The patch catalog was duplicated scaffolding logic running in parallel with the one cps-init already drives.

**Replacement upgrade model:** two entry points, no patcher.

| Upgrade surface | Entry point |
|---|---|
| Scaffold drift (dirs, buckets, canonical docs, CLAUDE.md section blocks) | `cps-init` — re-run against project |
| Runtime drift (`.cps/*.py`) | `cps-setup` → "Upgrade runtime" profile |
| Destructive reset | `cps-setup` → "Reinstall" profile |

**Bootstrap walkthrough:** `Reference/Patterns/cps-bootstrap-new-project.md`.

**Do not reuse these files.** Content blobs here are frozen at p001–p007 and will drift from `cps_scaffold.py` over time. Kept for audit trail only.
