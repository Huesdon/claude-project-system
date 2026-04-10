# Delegate CPS scaffolding to externally-managed CMD+PS1 pair

**Date:** 2026-04-09
**Status:** Accepted

## Context
The `cps-init` skill historically built the CPS project scaffold (Reference/ buckets, `_INDEX.md` stubs, canonical docs) via inline logic inside the skill prose. This consumed significant tokens on every install, coupled scaffold edits to the skill rebundle cycle, and forced Claude to classify and repair scaffold state during init (the REPAIRED / Step 6 flag machinery). Any scaffold structure change meant rebundling the skill and propagating a new `.skill` file.

## Decision
Move scaffolding out of the skill entirely. The scaffold is produced by a local Windows CMD + PowerShell pair that lives in the project repo at `Reference/cps-scaffold.cmd` and `Reference/cps-scaffold.ps1`. The `cps-init` skill becomes a thin wrapper that (1) verifies both files exist, (2) prompts the user to double-click `cps-scaffold.cmd`, (3) waits for confirmation. The scripts are externally managed — they live in the repo, not inside the skill bundle, and update independently of the skill.

## Alternatives rejected
- **Keep inline scaffold logic in the skill** — expensive in tokens on every install, slow, coupled scaffold edits to the rebundle cycle.
- **Bundle the `.ps1` inside the `.skill` zip** — still requires a rebundle on every scaffold change, and forces extraction + exec-policy gymnastics at runtime.
- **Cross-platform via `pwsh` fallback on mac/Linux** — rejected for now. CPS install scope is Windows-only, simpler code path. Mac/Linux support deferred until concrete demand exists.

## Rationale
Pulls deterministic file creation out of token-expensive skill prose into a fast native script, **and** decouples scaffold edits from the skill rebundle cycle. The two concerns that drove the previous design — repair classification and cross-platform portability — are both explicitly retired as scope. Windows-only is an accepted boundary.

## Consequences
- `cps-init.skill` shrinks to a prompt-and-wait wrapper. Rewrite tracked as `t2-cps-init-skill-rewrite`.
- `cps-setup.skill` Core path must invoke cps-init as "run the cmd, then pillar setup" instead of embedding scaffolding logic.
- Any future scaffold structure change now edits `Reference/cps-scaffold.ps1` directly — no skill rebundle needed.
- The REPAIRED classification / Step 6 repair flag feature is retired. The MSB verify task (`t2-cps-init-msb-verify`) was superseded and marked complete on 2026-04-09.
- CPS becomes Windows-only in the install path. Non-Windows users cannot scaffold without a manual port.
- CLAUDE.md §4 and §7 need updates describing the new flow and flagging the scripts as externally managed — scope added to `t2-cps-claudemd-rev`.
- Setup Guide and Troubleshooting Guide need PS execution-policy and SmartScreen sections — scope added to `t2-cps-docs-rewrite`.
