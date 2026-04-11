# Patch p001: Ideas + Roadmap Knowledge Buckets

**Applies to:** Core + Full
**Date added:** 2026-04-10

## Detection

Patch is PRESENT (skip) if ALL of the following are true:
- `Reference/Ideas/` directory exists
- `Reference/Ideas/_INDEX.md` exists
- `Reference/Roadmap/` directory exists
- `Reference/Roadmap/_INDEX.md` exists

If ANY check fails → patch is NEEDED.

## Actions

### 1. Create `Reference/Ideas/` directory
Create if not present.

### 2. Create `Reference/Ideas/_INDEX.md`

Write verbatim:

```markdown
# Ideas Index

Nascent ideas, exploration candidates, and "what if" items. Capture early, promote when ready.
Use `cps-capture` with trigger "add idea". Promote to Roadmap with "promote [title] to roadmap".

<!-- entries below -->
```

### 3. Create `Reference/Roadmap/` directory
Create if not present.

### 4. Create `Reference/Roadmap/_INDEX.md`

Write verbatim:

```markdown
# Roadmap Index

Committed intentions, not yet active tasks. Each item has a goal, rationale, and horizon (Now/Next/Later).
Use `cps-capture` with trigger "add to roadmap". Promote to tasks with "promote [title] to tasks".

<!-- entries below -->

| Title | Horizon | Status | File |
|-------|---------|--------|------|
```
