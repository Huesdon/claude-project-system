# CPS Dependency Persistence Investigation

> **Task:** `t3-cowork-dep-persistence-investigation`
> **Date:** 2026-04-08
> **Status:** Investigation complete — recommendation ready, implementation deferred to follow-up task
> **Related:** Phase 8.7 (rev 9 `_bootstrap_deps`), `t2-installer-rebuild-rev8`

---

## 1. Problem Statement

Phase 8.7 (rev 9) added `_bootstrap_deps()` to `cps_server.py`. It runs at module import, detects missing pip-installed packages via `try/except ImportError`, and reinstalls `sqlite-vec`, `huggingface-hub`, `tokenizers`, `onnxruntime`, and `numpy` via subprocess. This closed the silent MCP handshake failure that occurs when the Cowork sandbox resets pip state between sessions.

The fix is correct and shipping, but it pays a tax on every cold boot:

- **Warm pip cache:** ~3 seconds
- **Cold pip cache (first session ever, or wiped cache):** ~16 seconds
- **Worst case (sqlite-vec wheel build from source on cold cache):** up to ~20 seconds

This delay is silent — the MCP server shows no startup output until handshake completes — so a slow boot looks like a frozen tool to the user.

The goal of this investigation: find a durable persistence path that eliminates the per-session reinstall cost without re-introducing the silent failure mode rev 9 fixed.

---

## 2. Sandbox Filesystem Map

The first thing to establish: what actually persists in a Cowork sandbox vs what gets wiped on session start.

### 2.1 Mount Table (relevant rows)

| Mount Point | Type | Backed By | Persistence |
|---|---|---|---|
| `/sessions` (root) | ext4 (rw) on `/dev/sdc` | virtio block device | **Ephemeral** — recycled per session |
| `/sessions/<session-id>/mnt/CPS` | bindfs (FUSE, rw) | Windows host folder via virtiofs | **Persistent** — IS the user's actual folder |
| `/sessions/<session-id>/mnt/.claude/skills` | FUSE (ro) | Skill bundle from Cowork install | Persistent but read-only |
| `/sessions/<session-id>/mnt/.cowork-lib` | FUSE (ro) | `shim.sh` | Persistent but read-only |
| `/sessions/<session-id>/.local`, `.cache/pip` | (none) | local filesystem under ephemeral $HOME | **Ephemeral** — does not exist on fresh session |

The session-id-named directory `/sessions/trusting-modest-ptolemy/` is itself ephemeral and gets a new UUID on every Cowork session start. Anything written to `$HOME` (which IS that directory) does not survive.

### 2.2 Persistence Verdicts

| Path | Survives Session? | Why |
|---|---|---|
| `~/.cache/pip` | **No** | $HOME wipes per session. Confirmed empty on fresh boot. |
| `~/.local/lib/python3.10/site-packages` | **No** | Same — this is exactly what rev 9 had to work around. |
| `/usr/local/lib/python3.10/dist-packages` | **Yes** but read-only without sudo. `numpy` and `onnxruntime` already live here. |
| `mnt/CPS/.cps/` | **Yes** | Bindfs to the user's Windows folder. The existing `cps.db` proves persistence — it survives across sessions. |

### 2.3 The bindfs `rm` Quirk

The `mnt/CPS` bindfs mount returns `Operation not permitted` on `rm`. This is by design — that's why `mcp__cowork__allow_cowork_file_delete` exists. Files can be created and overwritten freely, but deletion requires the cowork delete tool.

Implication: any persistence strategy that involves "delete old version, install new version" needs an in-place overwrite path. Options that try to clean stale state via `rm -rf` will accumulate `.fuse_hidden*` ghost files and `.dist-info` siblings.

The existing `.cps/` already shows 7 `.fuse_hidden0000XXX` files left behind from prior SQLite WAL kills — proof that the bindfs gotcha is not theoretical.

---

## 3. The Four Options Evaluated

### 3.1 Option 1 — `~/.cache/pip` survival

**Hypothesis:** Pip wheel cache survives across sessions, so reinstall is fast even if site-packages is wiped.

**Verdict: Dead.** `~/.cache/pip` does not exist on a fresh session. `pip cache list` returns empty. The cache is in $HOME, which is ephemeral.

### 3.2 Option 2 — Symlink `~/.local` into the mounted folder

**Hypothesis:** Create a symlink from `~/.local/lib/python3.10/site-packages` to a directory inside `mnt/CPS/.cps/`, so user-site installs land on persistent storage.

**Verdict: Possible but pointless.** Symlinks from ephemeral $HOME to bindfs paths work (verified). But this requires bootstrap code to recreate the symlink on every session start, and it depends on pip honoring user-site, which isn't guaranteed under `--break-system-packages`. Option 3 achieves the same outcome with no symlink layer and no pip-mode dependency.

### 3.3 Option 3 — `pip install --target .cps/deps` + `PYTHONPATH`

**Hypothesis:** Install deps directly into a mounted directory using pip's `--target` flag, then add that directory to `PYTHONPATH` so Python finds them at import time. No venv. No symlink. No user-site.

**Verdict: This is the answer.** All four sub-checks passed:

| Check | Result |
|---|---|
| `pip install --target .cps/deps sqlite-vec huggingface-hub tokenizers` | Installed cleanly. 49 MB total. 16.5s on cold network. |
| `PYTHONPATH=.cps/deps python3 -c "import sqlite_vec, huggingface_hub, tokenizers"` | All three import. `sqlite_vec.__file__` resolves under the mounted path. |
| `numpy` and `onnxruntime` still resolve from `/usr/local/lib/python3.10/dist-packages/` (not duplicated) | Yes — they're system-wide already, so we only ship the 3 missing deps. |
| Persistence across sessions | Guaranteed by bindfs — `.cps/cps.db` already proves this works. |

**Cold-boot cost comparison:**

```
rev 9 _bootstrap_deps (warm pip cache):  3.1s
rev 9 _bootstrap_deps (cold pip cache):  ~16.5s
PYTHONPATH approach:                     0.214s
```

**Speedup: 14.5× warm, ~80× cold.**

### 3.4 Option 4 — Cowork dep-preinstall hook

**Hypothesis:** Cowork's `.mcp.json` schema supports a `setup`, `init`, or `preinstall` field that runs before the MCP server boots, letting CPS declare its deps and have Cowork install them.

**Verdict: Doesn't exist.** The `.mcp.json` schema is `command` / `args` / `env`. No setup hook. No init step. No declarative dep field.

**But the `env` field is the actual hook.** It can carry `PYTHONPATH=.cps/deps`, which is exactly what option 3 needs to wire the persistent deps directory into the launched server's import path.

---

## 4. Recommended Architecture

**Core idea:** Ship deps inside `.cps/deps/`, wire them via `PYTHONPATH` in `.mcp.json` env, keep rev 9 `_bootstrap_deps` as a fallback safety net.

### 4.1 Layout

```
mnt/CPS/.cps/
├── cps.db                  ← existing SQLite vector store
├── cps_server.py           ← existing runtime
├── cps_chunker.py          ← existing runtime
├── cps_embedder.py         ← existing runtime
├── cps_graph.py            ← existing runtime
├── cps_test_suite.py       ← existing runtime
├── cps_config.json         ← existing config
├── cps_manifest.json       ← existing manifest
└── deps/                   ← NEW: pip install --target output
    ├── sqlite_vec/
    ├── huggingface_hub/
    ├── tokenizers/
    ├── hf_xet/             ← transitive dep of huggingface-hub (~11 MB)
    ├── pygments/           ← transitive (~8 MB, can be pruned later)
    ├── ...
    └── *.dist-info/
```

Total `.cps/deps/` size: **~49 MB** with transitives. Could be trimmed by ~20 MB if `pygments` and a few other transitives are pruned (they're huggingface-hub's CLI optionals that the CPS server never imports).

### 4.2 `.mcp.json` Update

Current template:

```json
{
  "mcpServers": {
    "cps": {
      "type": "stdio",
      "command": "python",
      "args": [".cps/cps_server.py", "--serve"],
      "env": {
        "CPS_CONFIG_PATH": ".cps/cps_config.json"
      }
    }
  }
}
```

New template:

```json
{
  "mcpServers": {
    "cps": {
      "type": "stdio",
      "command": "python",
      "args": [".cps/cps_server.py", "--serve"],
      "env": {
        "CPS_CONFIG_PATH": ".cps/cps_config.json",
        "PYTHONPATH": ".cps/deps"
      }
    }
  }
}
```

One field added. That's the entire wiring change.

### 4.3 Layered Dep Resolution

The new boot sequence:

1. **Cowork launches `python .cps/cps_server.py --serve` with `PYTHONPATH=.cps/deps`.**
2. **`cps_server.py` module-level `_bootstrap_deps()` runs.** It tries to import each dep. If `PYTHONPATH=.cps/deps` is set and the deps are present, all imports succeed in ~0.2s and `_bootstrap_deps` returns immediately with a no-op.
3. **If imports fail** (deps directory missing or corrupted), `_bootstrap_deps` falls through to its current behavior: `pip install ... --break-system-packages` to ephemeral `~/.local`. Slow (~3-16s), but the server still boots.

This is belt-and-suspenders. The fast path is the new `.cps/deps/` directory. The slow path is rev 9. Either way, the server boots successfully — the silent-failure mode rev 9 closed stays closed.

### 4.4 cps-installer Step Layout

The installer needs one new step (call it Step 4.5, between "wire .mcp.json" and "namespace registration"):

> **Step 4.5 — Install Python dependencies into `.cps/deps/`.** Run `pip install --target .cps/deps sqlite-vec huggingface-hub tokenizers --quiet`. Time it (typical 15–20s on cold network, 3–5s on warm). Validate by spawning a subprocess with `PYTHONPATH=.cps/deps python3 -c "import sqlite_vec, huggingface_hub, tokenizers; print('OK')"`. If validation fails, halt with a clear error message; do not silently fall through to rev 9 bootstrap (we want the installer to be authoritative).

Step 4.5 is the only new installer step. The `.mcp.json` wiring step (currently Step 5 in cps-installer) gains one extra `env` key. Steps 11.5, 11.6, 13 are unchanged.

### 4.5 Upgrade Path

When upgrading deps to a new version of CPS:

```bash
pip install --target .cps/deps --upgrade sqlite-vec huggingface-hub tokenizers
```

This overwrites in place. The old `.dist-info` directories accumulate (because bindfs blocks `rm`), which is cosmetic but harmless — Python uses the highest-version `.dist-info` it finds. A periodic `task` entry to call `mcp__cowork__allow_cowork_file_delete` and clean stale `.dist-info` siblings is the long-term hygiene play, but it's not blocking.

---

## 5. Open Questions Before Implementation

These are the design calls that need a decision before the implementation task starts. Documenting them here so the next session doesn't have to re-derive them.

1. **Transitive pruning.** `.cps/deps/` is 49 MB with full transitives. About 20 MB of that is `pygments`, `rich`, `click`, and other CLI-optional deps that huggingface-hub pulls in but cps_server.py never imports. Worth a `pip install --no-deps` + manual transitive curation pass to get under 30 MB? Or accept the 49 MB and move on?
2. **Version pinning.** Should the installer pin exact versions (`sqlite-vec==0.1.9`, etc.) or accept whatever pip resolves at install time? Pinning protects against upstream API breakage; floating keeps the installer one-line simple. Recommendation: pin in the installer, document the pinned versions in CLAUDE.md §3, bump intentionally.
3. **`.dist-info` cleanup cadence.** Bindfs blocks `rm`, so upgrades leave stale `.dist-info` directories. Three options: (a) manual cleanup task once a quarter, (b) installer always nukes `.cps/deps/` via `mcp__cowork__allow_cowork_file_delete` and reinstalls fresh on every CPS upgrade, (c) ignore it entirely and let the cruft accumulate. Recommendation: option (b) on installer upgrade only — clean reinstall is the simplest mental model.
4. **Tier 1 vs Tier 2 rollout.** Should `.cps/deps/` ship in the next cps-installer rebuild (rev 8 — already pending as `t2-installer-rebuild-rev8`), or wait for a separate rev 9? Recommendation: bundle into rev 8. The rebuild is already on the queue and the change is small (one new step + one `env` key).
5. **Self-hosting impact.** This project (CPS Runtime) currently runs `python Runtime/cps_server.py` with whatever pip state the dev session has. Does the self-hosting `Runtime/` flow need its own `.cps/deps/` too? Probably not — devs working on Runtime can install deps however they like, and the rev 9 fallback covers them. The persistence story only matters for downstream Cowork projects that consume the installer.

---

## 6. Implementation Estimate

If the answers to §5 land cleanly:

- **Installer change:** ~30 minutes — one new step (4.5), one new `env` key in `.mcp.json` template, one validation subprocess call.
- **`cps_server.py` change:** None required for the fast path. Optional cleanup of `_bootstrap_deps` to detect "already loaded via PYTHONPATH" and skip the reinstall message.
- **Documentation:** Update CLAUDE.md §3 (Runtime Files / Dependencies section) to reflect the new layered model. Update CPS_Setup_Guide.md and CPS_Troubleshooting_Guide.md (already on the backlog as `t2-doc-drift-setup-troubleshooting`).
- **Testing:** Wipe `.cps/` on a test project, run installer, confirm cold boot is sub-second after the install. Restart sandbox, confirm second cold boot is also sub-second (proves persistence). Delete `.cps/deps/`, confirm rev 9 fallback still boots the server.

Total: ~2 hours of focused work. Trivial compared to the rev 9 investigation.

---

## 7. Recommendation

**Bundle the `.cps/deps/` + `PYTHONPATH` change into `t2-installer-rebuild-rev8` rather than queuing a separate task.** Rev 8 is already on the backlog to ship the rev 9 `cps_server.py` patch. Adding the new installer step and the `.mcp.json` env key turns rev 8 from a single-purpose patch into a structural improvement, and avoids two installer rebuilds in two weeks.

The 14.5× / 80× speedup is real, the implementation is small, and the rev 9 fallback layer keeps the safety net intact.
