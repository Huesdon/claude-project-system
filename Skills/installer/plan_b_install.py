#!/usr/bin/env python3
"""
Plan B skill installer (PoC).

Fetches an unpacked skill source tree from github.com/Huesdon/claude-project-system
(main branch) per the shared skills-manifest.json, zips it locally into a .skill
file, and writes it to an output path the caller passes in.

Design notes
------------
- No binary .skill files live on the repo. The repo holds Skills/src/<name>/...
  trees plus Skills/src/skills-manifest.json. This script is the client-side
  zipper that reconstitutes an installable .skill on demand.
- Runs offline only on urllib — no third-party deps. Suitable for running inside
  a Cowork sandbox with no pip state.
- Claude (in the downstream session) is expected to call this with --name <skill>
  --out <path>, then hand the produced .skill file to mcp__cowork__present_files.
- Failure modes are explicit and atomic: we stage everything in a temp dir, and
  only rename into place on success.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

DEFAULT_RAW_BASE = "https://raw.githubusercontent.com/Huesdon/claude-project-system/main"
RAW_BASE = os.environ.get("PLAN_B_RAW_BASE", DEFAULT_RAW_BASE)
MANIFEST_URL = f"{RAW_BASE}/Skills/src/skills-manifest.json"


def _die(msg: str, code: int = 1) -> None:
    print(f"plan-b-install: ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def _fetch(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        _die(f"HTTP {e.code} fetching {url}")
    except urllib.error.URLError as e:
        _die(f"network error fetching {url}: {e.reason}")
    return b""  # unreachable


def load_manifest() -> dict[str, Any]:
    raw = _fetch(MANIFEST_URL)
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as e:
        _die(f"manifest at {MANIFEST_URL} is not valid JSON: {e}")
    if manifest.get("version") != 1:
        _die(f"unsupported manifest version: {manifest.get('version')!r}")
    if "skills" not in manifest or not isinstance(manifest["skills"], dict):
        _die("manifest missing 'skills' object")
    return manifest


def resolve_skill(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    skills = manifest["skills"]
    if name not in skills:
        available = ", ".join(sorted(skills.keys())) or "(none)"
        _die(f"skill '{name}' not in manifest. Available: {available}")
    entry = skills[name]
    if "path" not in entry or "files" not in entry:
        _die(f"skill '{name}' entry missing required keys 'path' and 'files'")
    if not isinstance(entry["files"], list) or not entry["files"]:
        _die(f"skill '{name}' has empty or invalid 'files' list")
    return entry


def stage_files(manifest: dict[str, Any], name: str, entry: dict[str, Any], staging: Path) -> list[Path]:
    src_root = manifest.get("src_root", "Skills/src").rstrip("/")
    skill_path = entry["path"].rstrip("/")
    files = entry["files"]
    staged: list[Path] = []
    for rel in files:
        url = f"{RAW_BASE}/{src_root}/{skill_path}/{rel}"
        content = _fetch(url)
        dest = staging / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        staged.append(dest)
        print(f"  fetched {rel} ({len(content)} bytes)")
    return staged


def zip_skill(staging: Path, files: list[Path], out_path: Path) -> None:
    # Atomic: zip to a temp next to the final output, then rename on success.
    tmp_out = out_path.with_suffix(out_path.suffix + ".partial")
    with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            arcname = f.relative_to(staging).as_posix()
            zf.write(f, arcname)
    os.replace(tmp_out, out_path)


def install(name: str, out_path: Path) -> None:
    print(f"plan-b-install: resolving '{name}' from {MANIFEST_URL}")
    manifest = load_manifest()
    entry = resolve_skill(manifest, name)
    print(f"plan-b-install: staging {len(entry['files'])} file(s) from Skills/src/{entry['path']}/")
    with tempfile.TemporaryDirectory(prefix="plan-b-install-") as tmp:
        staging = Path(tmp)
        staged = stage_files(manifest, name, entry, staging)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        zip_skill(staging, staged, out_path)
    size = out_path.stat().st_size
    print(f"plan-b-install: wrote {out_path} ({size} bytes)")


def list_skills() -> None:
    manifest = load_manifest()
    for name, entry in sorted(manifest["skills"].items()):
        files = ", ".join(entry.get("files", []))
        desc = entry.get("description", "")
        print(f"  {name:<20} files=[{files}]  {desc}")


def main() -> int:
    p = argparse.ArgumentParser(
        prog="plan_b_install",
        description="Plan B skill installer — fetch unpacked src tree, zip client-side, emit .skill.",
    )
    p.add_argument("--name", help="Skill name to install (as it appears in skills-manifest.json)")
    p.add_argument("--out", help="Output .skill path (default: ./<name>.skill)")
    p.add_argument("--list", action="store_true", help="List all skills in the remote manifest and exit")
    args = p.parse_args()

    if args.list:
        list_skills()
        return 0

    if not args.name:
        p.error("--name is required (or use --list)")

    out = Path(args.out) if args.out else Path(f"{args.name}.skill")
    install(args.name, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
