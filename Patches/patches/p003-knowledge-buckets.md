# Patch p003: Core Knowledge Buckets (Patterns / Decisions / Lessons)

**Applies to:** Core + Full
**Date added:** 2026-04-08

## Detection

Patch is PRESENT (skip) if ALL of the following are true:
- `Reference/Patterns/` directory exists
- `Reference/Patterns/_INDEX.md` exists
- `Reference/Decisions/` directory exists
- `Reference/Decisions/_INDEX.md` exists
- `Reference/Lessons/` directory exists
- `Reference/Lessons/_INDEX.md` exists

If ANY check fails → patch is NEEDED.

## Actions

### 1. Create `Reference/Patterns/` directory
Create if not present.

### 2. Create `Reference/Patterns/_INDEX.md`

Write verbatim:

```markdown
# Patterns Index

Reusable techniques, design approaches, and workflows worth applying again.
Use `cps-capture` with trigger "save this pattern".

<!-- entries below -->

| Title | Tags | File |
|-------|------|------|
```

### 3. Create `Reference/Decisions/` directory
Create if not present.

### 4. Create `Reference/Decisions/_INDEX.md`

Write verbatim:

```markdown
# Decisions Index

ADR-style records: decision + context + alternatives rejected + rationale.
Use `cps-capture` with trigger "record this decision".

<!-- entries below -->

| Title | Date | File |
|-------|------|------|
```

### 5. Create `Reference/Lessons/` directory
Create if not present.

### 6. Create `Reference/Lessons/_INDEX.md`

Write verbatim:

```markdown
# Lessons Index

Gotchas, failure modes, and "next time do X" entries.
Use `cps-capture` with trigger "lesson learned".

<!-- entries below -->

| Title | Date | File |
|-------|------|------|
```
