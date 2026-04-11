#!/usr/bin/env python3
"""CPS Validation Test Suite
Tests all major CPS tool surfaces via the JSON-RPC 2.0 protocol over subprocess stdio.
Run from: project root (path resolved dynamically via __file__)
"""

import subprocess
import sys

_REQUIRED = ["sqlite-vec", "huggingface-hub", "tokenizers", "onnxruntime", "numpy"]

def _bootstrap_deps():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", *_REQUIRED,
         "--break-system-packages", "-q"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("ERROR: dependency install failed during bootstrap.")
        print(result.stderr)
        sys.exit(1)

_bootstrap_deps()

import json
import time
import os
from pathlib import Path
from typing import Any
