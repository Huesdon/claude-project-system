# CPS Patch Index

Lightweight catalog for `cps-patcher`. Detection checks live here (compact form). Full patch actions are in per-patch files under `patches/` — fetched lazily only when detection says a patch is needed.

**IMPORTANT — Sentinel check:** After reading this file, verify the sentinel at EOF matches the last row's ID. If the sentinel is missing or mismatched, abort with: `ERROR: patch-index.md appears truncated — last sentinel does not match. Aborting to prevent silent partial patching.`

---

| # | ID | Profile | File |
|---|----|---------|----|
| 1 | p001-ideas-roadmap | Both | patches/p001-ideas-roadmap.md |
| 2 | p002-documentation-scaffold | Both | patches/p002-documentation-scaffold.md |
| 3 | p003-input-output-dirs | Both | patches/p003-input-output-dirs.md |
| 4 | p004-cps-task-module-doc | Both | patches/p004-cps-task-module-doc.md |
| 5 | p005-cps-toc-rule-doc | Both | patches/p005-cps-toc-rule-doc.md |
| 6 | p006-cps-core-block-rev3 | Both | patches/p006-cps-core-block-rev3.md |

---

## Detection blocks

Detection for each patch is defined below. ALL checks in a block must pass for the patch to be considered already present. If ANY check fails, the patch is needed.

---

### p001-ideas-roadmap

1. `Reference/Ideas/` directory exists
2. `Reference/Ideas/_INDEX.md` exists
3. `Reference/Roadmap/` directory exists
4. `Reference/Roadmap/_INDEX.md` exists
5. `CLAUDE.md` §12 section contains both "Ideas" and "Roadmap"
6. `Reference/Claude/CPS_Capture_Taxonomy.md` contains `<!-- rev: 2 -->` (five-bucket version marker)

Notes: For check 5 — if no CLAUDE.md exists, treat as failed. For check 6 — if the file doesn't exist, treat as skipped (don't create it from scratch).

---

### p002-documentation-scaffold

1. `Documentation/` directory exists
2. `Documentation/md/` directory exists

---

### p003-input-output-dirs

1. `Input/` directory exists
2. `Output/` directory exists

---

### p004-cps-task-module-doc

1. `Reference/Claude/CPS_Task_Module.md` exists
2. `Reference/Claude/CPS_Task_Module.md` contains `<!-- rev: 2 -->`

---

### p005-cps-toc-rule-doc

1. `Reference/Claude/CPS_TOC_Rule.md` exists
2. `Reference/Claude/CPS_TOC_Rule.md` contains `<!-- rev: 1 -->`

---

### p006-cps-core-block-rev3

1. `CLAUDE.md` exists
2. `CLAUDE.md` contains `<!-- cps-core BEGIN rev: 3 -->`

Notes: For check 1 — if no CLAUDE.md exists, skip patch and note in report. For check 2 — if CLAUDE.md exists but contains rev 1, rev 2, or no cps-core block, patch is needed.

---

<!-- CATALOG_END p006-cps-core-block-rev3 -->
