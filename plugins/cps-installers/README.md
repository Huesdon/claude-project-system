# cps-installers

On-demand install-time skills for the Claude Project System (CPS). Split out of the global `/mnt/.claude/skills/` install to avoid paying ~400–600 tokens of skill-description overhead on every session, since CPS only needs these two skills at the moment of scaffolding or runtime deploy.

## What's in this plugin

| Skill | Purpose |
|---|---|
| `cps-init` | Scaffolds a new project: `Reference/` tree, canonical docs, CLAUDE.md §9/§11/§12 pointer sections. Fetches `cps_scaffold.py` from GitHub at runtime. |
| `cps-setup` | Deploys CPS into a project. Core = scaffold only. Full = Core + `.cps/` Python runtime + semantic index + knowledge graph. Fetches `Runtime/*.py` from GitHub at runtime. |

`cps-patcher` (retired in CPS Phase 8.8) is intentionally excluded.

## Install (per project)

From inside the target Cowork project, register the marketplace once globally, then install the plugin with project scope so it only loads in the one project that needs it:

```
/plugin marketplace add Huesdon/cowork-project-system
/plugin install cps-installers@cps --scope project
```

After the scaffold + runtime deploy is done, disable or uninstall the plugin to drop the token overhead:

```
/plugin disable cps-installers
```

Re-enable on demand for force-upgrades or runtime redeploys.

## Why two skills, not one

`cps-init` and `cps-setup` have distinct lifecycles. `cps-init` is pure scaffold and can run standalone on a Core-only project. `cps-setup` depends on `cps-init` having run and adds the Full-profile runtime on top. Keeping them separate preserves the Core → Full upgrade path without requiring a single monolithic installer.

## Runtime source of truth

Python runtime lives at `Runtime/*.py` in the CPS repo. `cps-setup` fetches each file at deploy time via `curl` against `raw.githubusercontent.com/Huesdon/cowork-project-system/main/Runtime/<file>.py` and verifies size + shebang + `py_compile` before writing to `.cps/`. No runtime Python is bundled inside this plugin — the plugin is SKILL.md only.

## Related skills (global, not in this plugin)

`cps-query`, `cps-refresh`, `cps-capture`, and `task` remain in global `/mnt/.claude/skills/`. They are operational (day-to-day use), not install-time.
