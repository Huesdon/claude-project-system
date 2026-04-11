# CPS is a solo-developer system

**Date:** 2026-04-11
**Status:** Accepted (scope-corrected 2026-04-11)
**Supersedes in part:** The original "permanently single-tenant" framing, which conflated "one developer" with "one project." The axis was wrong — CPS is solo-developer, one-machine, **multi-project**. Skills install globally once; any number of Cowork project folders can be scaffolded. See `2026-04-11-cps-upgrade-model-two-entry-points.md` for the scope correction trigger.

## Context

CPS has been built and operated as a one-developer, one-machine system since inception — Shane Huesdon, one machine, and (originally) one forever-home project folder holding the CPS runtime and all design docs. As CPS matured, it became clear that the correct usage pattern is the opposite of what the first draft of this decision captured: CPS scaffolds, indexes, and manages **many** Cowork project folders from a single global skill install. The forever-home project is the *source of truth for CPS itself*, not the only project that runs CPS.

Repeated design pressure still surfaces on the margins: "should the installer support multi-tenant deployments," "should skills be distributable across machines," "what about a shared registry," "what about cross-machine bootstrap." Each of those questions costs real design time and opens scope that will never have a consumer. A permanent anchor is needed so future Claude sessions (and future Shane) stop re-litigating the premise.

## Decision

CPS is a solo-developer, one-machine, multi-project system. One developer (Shane). One machine. One global skill install at `/mnt/.claude/skills/`. Any number of Cowork project folders scaffolded via `cps-init` / `cps-setup`. Every design, skill, and installer decision is evaluated under that constraint. Reject any premise that assumes multi-user sharing, fleet distribution, cross-machine sync, or a second developer consuming CPS.

The "one developer, one machine" axes are fixed. The "many projects" axis is the point — CPS exists to make every Cowork project folder benefit from the same scaffold, the same pillar skills, the same semantic index pipeline, without reinstalling anything global per project.

## Alternatives rejected

- **Multi-tenant-ready architecture (namespaces, user config, per-tenant DBs)** — rejected. No second tenant exists or is planned. Every namespace abstraction is dead weight and a latent source of bugs. "Many projects" does not imply "many tenants" — each project has its own local `.cps/` and its own `cps.db`; there is no shared per-tenant state to manage.
- **Skill distribution layer (registry, versioning, publish/subscribe)** — rejected. Skills are installed by hand via `.skill` bundles into `/mnt/.claude/skills/`. No one else needs them. Updates happen by rebundling and reinstalling — a one-developer workflow.
- **Cross-machine state sync (cloud-hosted index, remote graph)** — rejected. Local SQLite + ONNX + project folder is the runtime. Cowork already handles the single-machine persistence story.
- **Patcher as a broadcast channel (push updates to N projects)** — rejected and retired. `cps-patcher` was built under the assumption that scaffold upgrades needed a separate incremental path from fresh installs. They don't: `cps_scaffold.py` is rev-aware and re-running `cps-init` is the canonical upgrade operation. Retirement captured in `2026-04-11-cps-upgrade-model-two-entry-points.md`.

## Rationale

Solo-developer-multi-project is the ground truth of how CPS is used and will be used. Designing for an imaginary fleet of developers adds schema complexity, auth surface, versioning overhead, and decision fatigue without ever being exercised. Committing to this in writing lets every subsequent design question collapse to its simplest form: the answer that works for one developer running many Cowork projects on one machine is the answer.

Tradeoffs explicitly accepted: CPS cannot be handed to another user without rework, and the code will not generalize cleanly if that ever becomes desirable. That rework cost is cheaper than paying a multi-tenant tax on every feature built between now and then.

## Consequences

- **Installer (`cps-setup`)**: no tenant argument, no user config file, no namespace flag beyond the project-folder-name display label. One install, many target projects.
- **Scaffold upgrades**: handled by re-running `cps-init` against any project folder. `cps_scaffold.py` is rev-gated and idempotent. No per-project patch catalog, no broadcast mechanism.
- **Skill distribution**: remains manual `.skill` bundle + hand-install into `/mnt/.claude/skills/`. No registry, no publish flow. Global install serves every project folder.
- **Schema (`cps.db`)**: no `tenant_id`, no `user_id`, no per-tenant tables. Each project has its own flat single-owner `cps.db`.
- **Runtime sync**: `Runtime/` → `.cps/` promotion stays project-local. Each project's `.cps/` is independent; no remote sync, no shared index.
- **Patcher retirement**: `cps-patcher` is retired. The upgrade surface is covered by `cps-init` (scaffold) and `cps-setup` "Upgrade runtime" (bytes). Details in `2026-04-11-cps-upgrade-model-two-entry-points.md`.
- **Future reversibility**: if CPS ever needs to become multi-developer, that is a ground-up rewrite, not a migration. This decision is the trade.
- **Future design questions**: "should CPS support X for other users/machines" → answer is no by default. Point at this decision.
