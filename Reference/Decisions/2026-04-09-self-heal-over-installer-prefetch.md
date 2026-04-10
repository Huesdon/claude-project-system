---
# Prefer runtime self-heal over installer pre-fetch for model downloads

**Date:** 2026-04-09
**Status:** Accepted

## Context
The 2026-04-09 cps-setup simulation found that on a truly fresh machine, `cps_embedder._ensure_loaded()` raised `FileNotFoundError` when `~/.cps/models/all-MiniLM-L6-v2/model.onnx` was absent. It did not call `download_model()` automatically. The cps-setup installer had no explicit pre-download step between pip install (Step 12) and initial ingest (Step 13), so the first ingest crashed. Two fix options were on the table: (a) add an installer step 12.5 that shells out to `download_model()`, or (b) make `_ensure_loaded()` self-heal by calling `download_model()` on miss.

## Decision
Fix it in the runtime via self-heal in `_ensure_loaded()`, not in the installer via a new pre-fetch step.

## Alternatives rejected
- **Installer Step 12.5 (pre-fetch via shell)** — rejected. Fixes only the cps-setup path. Any other caller (tests, direct imports, downstream scripts, future installers) still hits the same `FileNotFoundError`. Also couples the installer to an implementation detail of the embedder.
- **Require the user to run `download_model()` manually** — rejected. Surfaces an internal prerequisite as a user concern and violates the "install should just work" principle.

## Rationale
Self-heal in the runtime fixes every current and future caller in one place. The `download_model()` function is already idempotent (no-ops if files exist, logs "already cached"), so the self-heal is safe to call on every cold load. One edit to `cps_embedder.py` replaces a forever-growing list of installer patches. Tradeoff explicitly accepted: first-run embedding pays a ~90MB network download cost the first time it's invoked, rather than paying it earlier during install — this is the same total cost, just deferred to the actual point of need.

## Consequences
- cps-setup no longer needs a pre-fetch step; installer stays lean.
- Any downstream project, test harness, or script that imports `Embedder` inherits the fix for free.
- The first `embed_text()` call on a fresh machine now performs a network download and takes ~30s instead of ~100ms. Acceptable because it happens once per machine, logs clearly, and matches user expectations for first-run model loading.
- Future rule: prefer runtime self-heal for any installer-adjacent prerequisite check where the check is cheap and idempotent. Reserve installer steps for things the runtime genuinely can't discover or repair on its own.
