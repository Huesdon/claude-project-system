# Patch p002: Documentation Scaffold Directories

**Applies to:** Core + Full
**Date added:** 2026-04-09

## Detection

Patch is PRESENT (skip) if ALL of the following are true:
- `Documentation/` directory exists
- `Documentation/md/` directory exists

If ANY check fails → patch is NEEDED.

## Actions

### 1. Create `Documentation/` directory
Create if not present.

### 2. Create `Documentation/md/` directory
Create if not present.
