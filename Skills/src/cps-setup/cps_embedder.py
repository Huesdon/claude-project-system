"""CPS Embedding Generator
Generates 384-dimensional embeddings using all-MiniLM-L6-v2 ONNX model.

Downloads model from HuggingFace on first run, caches locally.
Uses onnxruntime (pre-installed in sandbox) for inference.
Uses HuggingFace tokenizers for text tokenization.
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)

# Model config
MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
MAX_SEQ_LENGTH = 256  # model's max; truncate longer inputs


def _legacy_model_dir() -> Path:
    """Project-local model directory used by older CPS installs."""
    return Path(__file__).parent / "models" / "all-MiniLM-L6-v2"


def _default_model_dir() -> Path:
    """Default location for cached model files.

    Returns ~/.cps/models/all-MiniLM-L6-v2/ unconditionally as the canonical
    cache so the model is shared across every CPS project on this machine and
    survives wipes of any individual project's .cps/ or Runtime/ directories.

    Falls back to a project-local Runtime/models/ path only if the shared
    location can't be created (e.g. read-only home, exotic sandbox). This
    fallback should be extremely rare in practice.
    """
    shared = Path.home() / ".cps" / "models" / "all-MiniLM-L6-v2"
    try:
        shared.mkdir(parents=True, exist_ok=True)
        return shared
    except (OSError, PermissionError):
        logger.warning(
            "Could not create shared model cache at %s; falling back to "
            "project-local path. Model will not be shared across projects.",
            shared,
        )
        return _legacy_model_dir()
