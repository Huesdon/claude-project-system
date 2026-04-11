# Patch p007 — Add `skills_version` to cps_config.json

**Profile:** Full only (Core has no `cps_config.json`)
**Idempotent:** Yes — detection gate prevents re-applying

---

## Detection

Pass (skip) if ALL of the following are true:
- `.cps/cps_config.json` exists
- The JSON contains a `"skills_version"` key (value may be null or a string)

Apply (needed) if:
- `.cps/cps_config.json` exists AND does NOT contain `"skills_version"`

Skip silently if:
- `.cps/cps_config.json` does not exist (Core install — not applicable)

---

## Actions

### Action 1 — Add `skills_version` key to `cps_config.json`

Read `.cps/cps_config.json` as JSON. Add the key:

```json
"skills_version": null
```

Write the updated JSON back to `.cps/cps_config.json` using `Path.write_text()`.

The `null` value signals "version unknown". The `cps-patcher` skill will populate
it with the actual release tag (e.g. `"skills-2026-04-10"`) on its next run when
it delivers a skill update via Step 6.5.

**Write rule:** Use `Path.write_text(json.dumps(config, indent=2))` — never bash
`echo` or `cp` on mounted folders.

---

## Expected outcome

`.cps/cps_config.json` contains `"skills_version": null` (or the tag string if
the patcher has already run after this patch).

Report: **UPDATED** `.cps/cps_config.json` — added `skills_version: null`.