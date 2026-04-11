"""CPS Document Chunker
Splits markdown and JSON files into semantically meaningful chunks.

Markdown chunking (original):
- Each ## or ### heading starts a new chunk
- Chunk metadata: source file, heading path, line range, word count
- Frontmatter extracted as separate metadata
- Chunks under 50 tokens merged with next chunk
- Chunks over 2000 tokens split at paragraph boundaries

JSON chunking (Phase 5.1):
- Top-level arrays: one chunk per array entry
- Top-level objects: one chunk per top-level key
- Nested structures serialized as pretty-printed JSON text
- Meta fields (keys starting with \"meta\" or \"_meta\") extracted as frontmatter
- Same Chunk dataclass, same ID scheme, same size constraints

Phase 7c: Structural repair for split JSON chunks.
- Oversized nested JSON split at line boundaries gets bracket-balance repair
- Unbalanced chunks get closing tokens appended + truncation comment prepended
- heading_path tagged with [truncated] for query-layer awareness
"""

import json as json_module
import re
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional


# Rough token estimate: ~1.3 tokens per word for English prose
TOKENS_PER_WORD = 1.3
MIN_TOKENS = 50
MAX_TOKENS = 2000
MIN_WORDS = int(MIN_TOKENS / TOKENS_PER_WORD)   # ~38
MAX_WORDS = int(MAX_TOKENS / TOKENS_PER_WORD)    # ~1538


@dataclass
class Chunk:
    chunk_id: str
    source_file: str
    heading_path: str          # e.g. \"Schema Definitions > flags.json > Fields\"
    text: str
    line_start: int
    line_end: int
    word_count: int
    estimated_tokens: int
    frontmatter: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _generate_chunk_id(source_file: str, heading_path: str, line_start: int, namespace: str = \"\") -> str:
    \"\"\"Deterministic chunk ID from source + heading + position.

    If namespace is provided, prefixes the hash: \"{namespace}:{hash}\".
    This prevents chunk ID collisions when multiple projects share a cross-project
    query layer or are registered in the same ProjectRegistry.
    \"\"\"
    raw = f\"{source_file}::{heading_path}::{line_start}\"
    hash_val = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f\"{namespace}:{hash_val}\" if namespace else hash_val