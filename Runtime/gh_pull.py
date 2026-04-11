#!/usr/bin/env python3
"""
gh_pull.py - GitHub-first recovery helper.

Fetches a file from the CPS GitHub repo and compares it against the local
copy. Used to recover from suspected Cowork file-truncation misreports or
VM<->Windows sync drift without trusting the local filesystem.

Repo: github.com/Huesdon/claude-project-system (public).
Fetches via raw.githubusercontent.com - same pattern cps-patcher uses.

Usage:
    python gh_pull.py <repo-relative-path> [--ref REF] [--apply] [--local PATH]

Examples:
    # Dry-run: fetch remote, hash-diff against local, report JSON
    python gh_pull.py Runtime/cps_server.py

    # Overwrite local with remote (auto-backups local first)
    python gh_pull.py Reference/CPS_Design.md --apply

    # Pull a specific tag/branch
    python gh_pull.py Runtime/cps_embedder.py --ref v8.7

Exit codes:
    0  success (match, diff reported, apply succeeded, or missing_local)
    2  fetch/IO error

Output: JSON on stdout with keys:
    path, ref, url, local_path,
    remote_size, remote_sha256,
    local_size, local_sha256,
    status (match | diff | missing_local | missing_remote | error),
    size_delta (on diff),
    applied, backup (on --apply),
    error (on error).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "Huesdon/claude-project-system"
DEFAULT_REF = "main"
DEFAULT_LOCAL_ROOT = Path("/sessions/zen-clever-goldberg/mnt/Claude Project System")
RAW_BASE = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_remote(repo_relpath: str, ref: str) -> bytes:
    url = RAW_BASE.format(repo=REPO, ref=ref, path=repo_relpath.replace("\\", "/"))
    req = urllib.request.Request(url, headers={"User-Agent": "cps-gh-pull/1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def build_url(repo_relpath: str, ref: str) -> str:
    return RAW_BASE.format(repo=REPO, ref=ref, path=repo_relpath.replace("\\", "/"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CPS GitHub-first recovery helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("path", help="Repo-relative path (e.g. Runtime/cps_server.py)")
    parser.add_argument("--ref", default=DEFAULT_REF, help="Git ref/branch/tag (default: main)")
    parser.add_argument("--apply", action="store_true", help="Overwrite local on diff (backs up local first)")
    parser.add_argument("--local", default=None, help="Override local file path (absolute)")
    parser.add_argument("--local-root", default=str(DEFAULT_LOCAL_ROOT), help="Local repo root (default: current CPS mount)")
    args = parser.parse_args()

    repo_relpath = args.path.replace("\\", "/").lstrip("/")
    local_path = Path(args.local) if args.local else Path(args.local_root) / repo_relpath

    result: dict = {
        "path": repo_relpath,
        "ref": args.ref,
        "url": build_url(repo_relpath, args.ref),
        "local_path": str(local_path),
    }

    # Fetch remote
    try:
        remote_bytes = fetch_remote(repo_relpath, args.ref)
    except urllib.error.HTTPError as e:
        result["status"] = "missing_remote" if e.code == 404 else "error"
        result["error"] = f"HTTP {e.code}: {e.reason}"
        print(json.dumps(result, indent=2))
        return 2
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {e}"
        print(json.dumps(result, indent=2))
        return 2

    result["remote_size"] = len(remote_bytes)
    result["remote_sha256"] = sha256_bytes(remote_bytes)

    # Read local
    if not local_path.exists():
        result["status"] = "missing_local"
        result["local_size"] = None
        result["local_sha256"] = None
        if args.apply:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(remote_bytes)
            result["applied"] = True
            result["backup"] = None
        print(json.dumps(result, indent=2))
        return 0

    local_bytes = local_path.read_bytes()
    result["local_size"] = len(local_bytes)
    result["local_sha256"] = sha256_bytes(local_bytes)

    if result["local_sha256"] == result["remote_sha256"]:
        result["status"] = "match"
        print(json.dumps(result, indent=2))
        return 0

    result["status"] = "diff"
    result["size_delta"] = result["remote_size"] - result["local_size"]

    if args.apply:
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup_path = local_path.with_suffix(local_path.suffix + f".local-backup-{ts}")
        backup_path.write_bytes(local_bytes)
        local_path.write_bytes(remote_bytes)
        result["applied"] = True
        result["backup"] = str(backup_path)
    else:
        result["applied"] = False
        result["hint"] = "re-run with --apply to overwrite local (auto-backup)"

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
