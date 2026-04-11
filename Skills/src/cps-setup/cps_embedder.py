"""
CPS Embedding Generator
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


def _migrate_legacy_model(target: Path) -> bool:
    """Move a legacy project-local model into the shared cache, if present.

    Returns True if a migration happened. Idempotent: safe to call every run.
    Only fires when the shared target is empty AND a populated legacy dir
    exists adjacent to this file. Uses shutil.move so the legacy copy is
    consumed (no orphaned 90MB blob left behind).
    """
    legacy = _legacy_model_dir()
    if legacy == target:
        return False  # fallback path is in use; nothing to migrate
    if not (legacy / "model.onnx").exists():
        return False
    if (target / "model.onnx").exists():
        return False  # shared cache already populated; legacy is just stale

    logger.info("Migrating legacy model cache: %s -> %s", legacy, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # If target dir was pre-created empty by _default_model_dir(), remove it
    # so shutil.move can place the legacy dir cleanly.
    try:
        if target.exists() and not any(target.iterdir()):
            target.rmdir()
    except OSError:
        pass
    try:
        shutil.move(str(legacy), str(target))
        return True
    except Exception as e:
        logger.warning("Legacy model migration failed: %s", e)
        return False


def download_model(model_dir: Optional[str] = None) -> Path:
    """
    Download ONNX model from HuggingFace if not already present.
    Returns path to the model directory.

    First attempts to migrate any legacy project-local cache into the shared
    ~/.cps/models/ location, so existing installs upgrade for free without
    re-downloading 90MB.
    """
    target = Path(model_dir) if model_dir else _default_model_dir()

    # One-time migration from legacy Runtime/models/ to shared cache
    _migrate_legacy_model(target)

    onnx_path = target / "model.onnx"
    tokenizer_path = target / "tokenizer.json"

    if onnx_path.exists() and tokenizer_path.exists():
        logger.info(f"Model already cached at {target}")
        return target

    target.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading {MODEL_REPO} to {target}...")

    from huggingface_hub import hf_hub_download

    # Download the ONNX model
    hf_hub_download(
        repo_id=MODEL_REPO,
        filename="onnx/model.onnx",
        local_dir=target,
    )
    # Move from onnx/ subdir to model dir root
    onnx_subdir = target / "onnx" / "model.onnx"
    if onnx_subdir.exists():
        onnx_subdir.rename(onnx_path)
        try:
            (target / "onnx").rmdir()
        except OSError:
            pass

    # Download tokenizer
    hf_hub_download(
        repo_id=MODEL_REPO,
        filename="tokenizer.json",
        local_dir=target,
    )

    # Download tokenizer config for special tokens
    try:
        hf_hub_download(
            repo_id=MODEL_REPO,
            filename="tokenizer_config.json",
            local_dir=target,
        )
    except Exception:
        pass  # not critical

    logger.info(f"Model downloaded to {target}")
    return target


class Embedder:
    """Generates embeddings using ONNX all-MiniLM-L6-v2."""

    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = Path(model_dir) if model_dir else _default_model_dir()
        self._session: Optional[ort.InferenceSession] = None
        self._tokenizer = None

    def _ensure_loaded(self):
        """Lazy-load model and tokenizer."""
        if self._session is not None:
            return

        onnx_path = self.model_dir / "model.onnx"
        tokenizer_path = self.model_dir / "tokenizer.json"

        if not onnx_path.exists() or not tokenizer_path.exists():
            logger.info(
                "ONNX model missing at %s — auto-downloading via download_model()",
                self.model_dir,
            )
            download_model(str(self.model_dir))

        # Load ONNX model
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 2
        self._session = ort.InferenceSession(
            str(onnx_path), opts, providers=["CPUExecutionProvider"]
        )

        # Load tokenizer
        from tokenizers import Tokenizer
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self._tokenizer.enable_truncation(max_length=MAX_SEQ_LENGTH)
        self._tokenizer.enable_padding(
            length=MAX_SEQ_LENGTH,
            pad_id=0,
            pad_token="[PAD]",
        )

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string. Returns 384-dim float32 array."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """
        Embed a batch of texts. Returns (N, 384) float32 array.
        Uses mean pooling over token embeddings with attention mask.
        """
        self._ensure_loaded()

        # Tokenize
        encodings = self._tokenizer.encode_batch(texts)

        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids, dtype=np.int64)

        # Run inference
        outputs = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )

        # outputs[0] is token embeddings: (batch, seq_len, 384)
        token_embeddings = outputs[0]

        # Mean pooling with attention mask
        mask_expanded = attention_mask[:, :, np.newaxis].astype(np.float32)
        sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
        sum_mask = np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
        embeddings = sum_embeddings / sum_mask

        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, a_min=1e-9, a_max=None)
        embeddings = embeddings / norms

        return embeddings.astype(np.float32)

    @property
    def dim(self) -> int:
        return EMBEDDING_DIM


if __name__ == "__main__":
    import sys

    # Download model if needed
    model_dir = download_model()
    print(f"Model ready at {model_dir}")

    # Quick test
    emb = Embedder(str(model_dir))
    test_texts = [
        "What fields does flags.json have?",
        "How does the startup scan work?",
        "Schema definitions for the handoffs file",
    ]
    vectors = emb.embed_batch(test_texts)
    print(f"Embedded {len(test_texts)} texts → shape {vectors.shape}")

    # Show similarity matrix
    sims = vectors @ vectors.T
    print("\nSimilarity matrix:")
    for i, t in enumerate(test_texts):
        for j, t2 in enumerate(test_texts):
            print(f"  [{i},{j}] {sims[i,j]:.3f}", end="")
        print()
