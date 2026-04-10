# CPS Git Workflow

> How to work with the `claude-project-system` GitHub repo from Windows and from Cowork sessions.

**Repo:** `https://github.com/Huesdon/claude-project-system` (public)  
**Default branch:** `main`  
**Commit identity:** Shane Huesdon <shane.huesdon@gmail.com>

---

## Why this matters

Cowork mounts corrupt git internal files (`.git/config` gets bad bytes, `.git/config.lock` sticks). This is the same class of issue as the old OneDrive path problem — a mount-layer limitation, not git's fault. **Never run `git init` or `git clone` inside a mounted folder.**

The workarounds:
1. **Clone outside the mount** (Linux sandbox path) — used for Cowork session pushes
2. **Clone on Windows** — used for Shane's local pulls and manual pushes

---

## Cowork session workflow (pushing changes)

Every Cowork session that needs to push to GitHub:

```bash
# 1. Get gh CLI (session-scoped — must reinstall each session)
cp /tmp/gh_2.89.0_linux_amd64/bin/gh /sessions/<session>/bin/gh
# If /tmp copy is gone, download fresh:
# curl -fsSL https://github.com/cli/cli/releases/download/v2.89.0/gh_2.89.0_linux_amd64.tar.gz | tar -xz -C /tmp

# 2. Clone OUTSIDE the mount (not inside /mnt/...)
cd /sessions/<session>
export GH_TOKEN="<your-pat>"
git clone "https://x-access-token:${GH_TOKEN}@github.com/Huesdon/claude-project-system.git" cps-clone

# 3. Configure identity
cd cps-clone
git config user.email "shane.huesdon@gmail.com"
git config user.name "Shane Huesdon"

# 4. Make changes inside cps-clone/ (NOT in the mounted folder)
# Edit files, add, commit, push as normal

# 5. Set remote URL with token for push
git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/Huesdon/claude-project-system.git"
git push origin main
```

**After pushing:** pull from Windows (below) to sync the mounted copy.

---

## Windows workflow (pulling/syncing)

From PowerShell or Git Bash on Windows:

```powershell
# First time setup (one-time)
cd "C:\path\to\your\CPS-project-folder"   # the folder Cowork mounts
git init
git remote add origin https://github.com/Huesdon/claude-project-system.git
git fetch origin
git checkout -b main origin/main

# Subsequent pulls
cd "C:\path\to\your\CPS-project-folder"
git pull origin main
```

**Note:** Git on Windows works fine inside the project folder — the Cowork mount corruption only affects the Linux session sandbox, not the underlying Windows filesystem.

---

## PAT management

- **Type:** Fine-grained PAT, `Huesdon/claude-project-system`, Contents + Administration read/write
- **Expiry:** Never expires (Shane's choice)
- **Storage:** Do NOT store in any file inside the mounted folder or committed to the repo. Keep in your password manager. Paste fresh into each Cowork session when needed.
- **Scrubbing:** After each session, the remote URL is set without the token embedded. The token lives only in the shell environment variable during the session.

---

## Patch catalog updates (adding new patches)

1. Open a Cowork session on this project
2. Run preflight (install gh CLI, clone to `cps-clone/`)
3. Edit `Patches/patch-index.md` — add table row, detection block, update sentinel to new last patch ID
4. Create `Patches/patches/<new-patch-id>.md` with the actions
5. Commit and push from `cps-clone/`
6. No skill rebundle needed — patcher WebFetches catalog from GitHub at runtime

---

## Repo structure

```
claude-project-system/
├── Patches/
│   ├── patch-index.md          # Lightweight index + detection + sentinel
│   └── patches/
│       ├── p001-ideas-roadmap.md
│       ├── p002-documentation-scaffold.md
│       ├── p003-input-output-dirs.md
│       ├── p004-cps-task-module-doc.md
│       ├── p005-cps-toc-rule-doc.md
│       └── p006-cps-core-block-rev3.md
├── Runtime/                    # Canonical Python source
├── Reference/                  # Design docs, decisions, lessons
├── Documentation/md/           # User-facing markdown docs
├── Skills/                     # Installable .skill bundles
└── .gitignore                  # Excludes .cps/*.db, Output/, etc.
```
