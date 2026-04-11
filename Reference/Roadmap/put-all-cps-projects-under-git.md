---
title: Put all CPS-enabled projects under git
horizon: Next
status: Open
captured: 2026-04-10
---

# Put All CPS-Enabled Projects Under Git

## Goal

Every Cowork project that has CPS installed should have its own git repo on GitHub (or another host), following the same pattern established for `cowork-project-system` itself.

## Rationale

Git gives each project:
- Full history and rollback
- A safe push/pull workflow for syncing between Cowork sessions (which can't reliably use the mount for git)
- A backup that survives session resets and Cowork updates

The pattern is proven (see `Reference/Claude/git-workflow.md`): clone outside the mount, work in the clone, pull from Windows to sync.

## Scope

Identify all active CPS-enabled projects (MSB, etc.) and set up one repo per project. Each gets:
- Its own private or public GitHub repo
- A tailored `.gitignore` (based on the CPS template — exclude `.cps/*.db`, `Output/`, etc.)
- The detached git dir workaround documented for Cowork sessions

## Horizon

**Next** — after patcher refactor lands (done 2026-04-10). Scope each project individually; one repo per project.

## How to apply

Use the workflow in `Reference/Claude/git-workflow.md`. Run `gh repo create` per project, then initial commit.
