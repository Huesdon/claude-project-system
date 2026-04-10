#!/usr/bin/env python3
"""
check_scaffold_parity.py — Pre-bundle assertion for cps-init.skill

Verifies that all 10 shared template strings in cps_scaffold.py and
cps-scaffold.ps1 are byte-identical. Run before rebundling cps-init.skill
to catch silent drift (§0 house rule: "template strings must stay in sync").

Usage:
    python3 Reference/check_scaffold_parity.py

Exit codes:
    0 — all 10 pairs match
    1 — one or more mismatches (details printed to stdout)
"""

import importlib.util
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate files relative to this script
# ---------------------------------------------------------------------------
HERE = Path(__file__).parent
PY_FILE = HERE / "cps_scaffold.py"
PS1_FILE = HERE / "cps-scaffold.ps1"

# ---------------------------------------------------------------------------
# The 10 template string pairs: (py_name, ps1_var_name)
# ---------------------------------------------------------------------------
PAIRS = [
    ("INDEX_PATTERNS",    "IndexPatterns"),
    ("INDEX_DECISIONS",   "IndexDecisions"),
    ("INDEX_LESSONS",     "IndexLessons"),
    ("INDEX_IDEAS",       "IndexIdeas"),
    ("INDEX_ROADMAP",     "IndexRoadmap"),
    ("TASK_MODULE",       "TaskModule"),
    ("TOC_RULE",          "TocRule"),
    ("CAPTURE_TAXONOMY",  "CaptureTaxonomy"),
    ("CORE_SECTION_BLOCK","CoreSectionBlock"),
    ("FULL_SECTION_BLOCK","FullSectionBlock"),
]

# ---------------------------------------------------------------------------
# Load Python constants via importlib (avoids sys.path side-effects)
# ---------------------------------------------------------------------------
def load_py_constants(path: Path) -> dict:
    spec = importlib.util.spec_from_file_location("cps_scaffold", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {name: getattr(mod, name) for name, _ in PAIRS}


# ---------------------------------------------------------------------------
# Extract PowerShell here-strings via regex
# PS1 here-string: $VarName = @'\n<content>\n'@
# Captures everything between the @' newline and the closing newline'@
# ---------------------------------------------------------------------------
def load_ps1_constants(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    result = {}
    for _, ps1_name in PAIRS:
        # Pattern: $VarName = @'\n ... \n'@
        pattern = (
            r"\$" + re.escape(ps1_name) +
            r"\s*=\s*@'\r?\n(.*?)\r?\n'@"
        )
        m = re.search(pattern, text, re.DOTALL)
        if m is None:
            result[ps1_name] = None  # not found
        else:
            # Normalise CRLF → LF so comparison is OS-agnostic
            content = m.group(1).replace("\r\n", "\n")
            # PS1 here-string content does not include the trailing newline
            # before '@ — but Python triple-quote strings do end with \n.
            # Add the trailing newline to match Python's representation.
            result[ps1_name] = content + "\n"
    return result


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------
def main():
    if not PY_FILE.exists():
        print(f"ERROR: {PY_FILE} not found")
        sys.exit(1)
    if not PS1_FILE.exists():
        print(f"ERROR: {PS1_FILE} not found")
        sys.exit(1)

    py_vals = load_py_constants(PY_FILE)
    ps1_vals = load_ps1_constants(PS1_FILE)

    mismatches = []
    missing_ps1 = []

    for py_name, ps1_name in PAIRS:
        py_val = py_vals.get(py_name)
        ps1_val = ps1_vals.get(ps1_name)

        if ps1_val is None:
            missing_ps1.append((py_name, ps1_name))
            continue

        if py_val != ps1_val:
            mismatches.append((py_name, ps1_name, py_val, ps1_val))

    # -----------------------------------------------------------------------
    # Report
    # -----------------------------------------------------------------------
    total = len(PAIRS)
    ok = total - len(mismatches) - len(missing_ps1)

    print(f"check_scaffold_parity — {total} pairs checked")
    print(f"  ✓ {ok} matching")

    if missing_ps1:
        print(f"  ✗ {len(missing_ps1)} missing in PS1:")
        for py_name, ps1_name in missing_ps1:
            print(f"      {py_name} / ${ps1_name} — not found in cps-scaffold.ps1")

    if mismatches:
        print(f"  ✗ {len(mismatches)} mismatch(es):")
        for py_name, ps1_name, py_val, ps1_val in mismatches:
            print(f"\n  --- {py_name} (Python) vs ${ps1_name} (PS1) ---")
            py_lines = py_val.splitlines()
            ps1_lines = ps1_val.splitlines()
            max_lines = max(len(py_lines), len(ps1_lines))
            diff_lines = []
            for i in range(max_lines):
                pl = py_lines[i] if i < len(py_lines) else "<missing>"
                sl = ps1_lines[i] if i < len(ps1_lines) else "<missing>"
                if pl != sl:
                    diff_lines.append(f"    line {i+1}:")
                    diff_lines.append(f"      py : {repr(pl)}")
                    diff_lines.append(f"      ps1: {repr(sl)}")
            print("\n".join(diff_lines))

    if mismatches or missing_ps1:
        print("\nFAIL — fix drift before rebundling cps-init.skill")
        sys.exit(1)
    else:
        print("\nPASS — safe to rebundle cps-init.skill")
        sys.exit(0)


if __name__ == "__main__":
    main()
